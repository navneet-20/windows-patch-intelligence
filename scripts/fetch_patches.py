"""
fetch_patches.py
Windows Patch Intelligence — Patch Tuesday Data Fetcher
Uses Gemini AI to fetch latest Windows 11 patch details from Microsoft catalog.
Runs on Patch Tuesday (2nd Tuesday of every month).
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
from google import genai

# ── Config ─────────────────────────────────────────────────────────────────────
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.6-flash"
DATA_DIR     = Path(__file__).parent.parent / "data"
PATCHES_CSV  = DATA_DIR / "patches.csv"
META_JSON    = DATA_DIR / "meta.json"
MAX_RETRIES  = 3
RETRY_DELAY  = 30

client = genai.Client(api_key=GEMINI_KEY)

def call_gemini(prompt: str) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            return response.text.strip().replace("```json", "").replace("```", "").strip()
        except Exception as e:
            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < MAX_RETRIES:
                print(f"  [RETRY {attempt}/{MAX_RETRIES}] Gemini busy, waiting {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                raise

def get_patch_tuesday(year: int, month: int) -> date:
    """Calculate the 2nd Tuesday of a given month."""
    first_day = date(year, month, 1)
    first_tuesday = first_day + timedelta(days=(1 - first_day.weekday()) % 7)
    return first_tuesday + timedelta(weeks=1)

def get_next_patch_tuesday() -> date:
    today = date.today()
    current_pt = get_patch_tuesday(today.year, today.month)
    if today <= current_pt:
        return current_pt
    # Move to next month
    if today.month == 12:
        return get_patch_tuesday(today.year + 1, 1)
    return get_patch_tuesday(today.year, today.month + 1)

def get_current_patch_tuesday() -> date:
    today = date.today()
    current_pt = get_patch_tuesday(today.year, today.month)
    if today >= current_pt:
        return current_pt
    # Last month's patch tuesday
    if today.month == 1:
        return get_patch_tuesday(today.year - 1, 12)
    return get_patch_tuesday(today.year, today.month - 1)

def fetch_patch_data() -> list[dict]:
    today = date.today()
    month_name = today.strftime("%B")
    year = today.year

    prompt = f"""
You are a Windows security expert. Today is {today.strftime("%B %d, %Y")} and it's Patch Tuesday.

Fetch the latest {month_name} {year} Windows 11 cumulative update details from Microsoft.

For Windows 11 24H2 and 23H2, provide the exact KB numbers and build versions released this month.

Return ONLY a valid JSON array with NO markdown:
[
  {{
    "Month": "{month_name}",
    "Year": "{year}",
    "Patch_Date": "{today.strftime('%Y-%m-%d')}",
    "KB_Number": "KB5XXXXXXX",
    "Version": "26200.XXXX",
    "OS": "Windows 11 24H2",
    "Title": "Exact Microsoft title of the update",
    "Description": "2-3 sentence description of what this update fixes - focus on security areas patched",
    "Download_URL": "https://catalog.update.microsoft.com/Search.aspx?q=KB5XXXXXXX",
    "Severity": "Critical or Important",
    "CVE_Count": 0,
    "Is_Latest": true
  }},
  {{
    "Month": "{month_name}",
    "Year": "{year}",
    "Patch_Date": "{today.strftime('%Y-%m-%d')}",
    "KB_Number": "KB5XXXXXXX",
    "Version": "22621.XXXX",
    "OS": "Windows 11 23H2",
    "Title": "Exact Microsoft title of the update",
    "Description": "2-3 sentence description",
    "Download_URL": "https://catalog.update.microsoft.com/Search.aspx?q=KB5XXXXXXX",
    "Severity": "Critical or Important",
    "CVE_Count": 0,
    "Is_Latest": false
  }}
]

Use real KB numbers from the Microsoft Security Update Guide for {month_name} {year}.
If you are not certain of exact KB numbers, provide your best knowledge and note uncertainty in Description.
"""
    try:
        text = call_gemini(prompt)
        return json.loads(text)
    except Exception as e:
        print(f"[ERROR] Failed to fetch patch data: {e}")
        return []

def update_meta(current_pt: date, next_pt: date):
    today = date.today()
    days_since = (today - current_pt).days
    days_until  = (next_pt - today).days

    meta = {
        "current_patch_date":  current_pt.strftime("%Y-%m-%d"),
        "current_patch_day":   current_pt.strftime("%A"),
        "current_patch_month": current_pt.strftime("%B"),
        "current_patch_year":  str(current_pt.year),
        "next_patch_date":     next_pt.strftime("%Y-%m-%d"),
        "next_patch_day":      next_pt.strftime("%A"),
        "next_patch_month":    next_pt.strftime("%B"),
        "next_patch_year":     str(next_pt.year),
        "days_since_patch":    days_since,
        "days_until_next":     days_until,
        "news_window_active":  0 <= days_since <= 7,
        "last_updated":        str(today),
    }
    with open(META_JSON, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  ✅ meta.json updated — days since patch: {days_since}, days until next: {days_until}")

def run():
    print("=" * 60)
    print(f"Windows Patch Intelligence — Patch Fetcher | {GEMINI_MODEL}")
    print("=" * 60)

    current_pt = get_current_patch_tuesday()
    next_pt    = get_next_patch_tuesday()
    print(f"\n📅 Current Patch Tuesday: {current_pt.strftime('%B %d, %Y')}")
    print(f"📅 Next Patch Tuesday:    {next_pt.strftime('%B %d, %Y')}")

    # Update meta.json
    update_meta(current_pt, next_pt)

    # Fetch new patch data
    print(f"\n🤖 Fetching patch data from Gemini...\n")
    new_patches = fetch_patch_data()

    if not new_patches:
        print("[EXIT] No patch data returned.")
        sys.exit(0)

    # Load existing patches
    if PATCHES_CSV.exists():
        df = pd.read_csv(PATCHES_CSV)
        # Mark all existing as not latest
        df["Is_Latest"] = False
    else:
        df = pd.DataFrame()

    # Add new patches (avoid duplicates by KB number)
    existing_kbs = df["KB_Number"].tolist() if not df.empty else []
    new_rows = []
    for p in new_patches:
        if p.get("KB_Number") not in existing_kbs:
            new_rows.append(p)
            print(f"  ✅ Added: {p.get('KB_Number')} — {p.get('OS')} ({p.get('Version')})")
        else:
            print(f"  [SKIP] Already exists: {p.get('KB_Number')}")

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([new_df, df], ignore_index=True)  # New patches at top

    df.to_csv(PATCHES_CSV, index=False)
    print(f"\n✅ patches.csv updated — {len(df)} total patches")

if __name__ == "__main__":
    run()
