"""
fetch_articles.py
Windows Patch Intelligence — News Article Fetcher
Uses Gemini AI to crawl major tech sources for Windows 11 patch news.
Runs daily for 7 days after each Patch Tuesday.
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
ARTICLES_CSV = DATA_DIR / "articles.csv"
META_JSON    = DATA_DIR / "meta.json"
MAX_RETRIES  = 3
RETRY_DELAY  = 30

SOURCES = [
    "BleepingComputer",
    "The Verge",
    "Ars Technica",
    "Windows Central",
    "Petri",
    "Neowin",
    "Microsoft Tech Community Blog",
    "ZDNet",
    "TechRadar",
    "9to5Google",
]

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
CATEGORY_OPTIONS = ["Security", "Reliability", "Performance", "Known Issues", "IT Pro", "Feature"]

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

def load_meta() -> dict:
    if META_JSON.exists():
        with open(META_JSON) as f:
            return json.load(f)
    return {}

def fetch_articles(patch_date: str, patch_kb: str) -> list[dict]:
    today = date.today()
    sources_str = ", ".join(SOURCES)

    prompt = f"""
You are a Windows security and IT journalist. Today is {today.strftime("%B %d, %Y")}.

The latest Windows 11 Patch Tuesday was on {patch_date} ({patch_kb}).

Search your knowledge for real news articles and reports published between {patch_date} and today
from these major tech sources: {sources_str}

Find articles about:
1. Critical security vulnerabilities patched
2. Known bugs or issues introduced by the patch
3. Zero-days and actively exploited CVEs
4. IT admin deployment guidance
5. Reliability or performance improvements
6. Windows health and stability focus areas

Return ONLY a valid JSON array with NO markdown, up to 8 articles:
[
  {{
    "Date": "YYYY-MM-DD",
    "Title": "Exact or close to real article title",
    "Summary": "2-3 sentence factual summary of what the article covers",
    "Source": "Source name from the list",
    "URL": "https://real-article-url-if-known-or-source-homepage",
    "Priority": "Critical or High or Medium or Low",
    "Category": "Security or Reliability or Performance or Known Issues or IT Pro or Feature",
    "KB_Reference": "{patch_kb}",
    "Is_Current_Month": true
  }}
]

Priority rules:
- Critical: Zero-days, actively exploited CVEs, critical RCE bugs
- High: Important security patches, known issues affecting many users
- Medium: Reliability improvements, IT deployment guides
- Low: Minor features, cosmetic fixes

Focus on REAL reported issues. Be specific about what areas of Windows were fixed.
"""
    try:
        text = call_gemini(prompt)
        return json.loads(text)
    except Exception as e:
        print(f"[ERROR] Failed to fetch articles: {e}")
        return []

def run():
    print("=" * 60)
    print(f"Windows Patch Intelligence — Article Fetcher | {GEMINI_MODEL}")
    print("=" * 60)

    meta = load_meta()
    if not meta:
        print("[ERROR] meta.json not found. Run fetch_patches.py first.")
        sys.exit(1)

    current_patch_date = meta.get("current_patch_date", "")
    days_since = meta.get("days_since_patch", 99)
    news_active = meta.get("news_window_active", False)

    print(f"\n📅 Current Patch Tuesday: {current_patch_date}")
    print(f"⏱  Days since patch: {days_since}")
    print(f"📰 News window active: {news_active}")

    if not news_active:
        print("\n[INFO] Outside 7-day news window. Skipping article fetch.")
        sys.exit(0)

    # Get KB reference for current patch
    kb_ref = "KB5041585"  # Default fallback
    if ARTICLES_CSV.exists():
        patches_csv = DATA_DIR / "patches.csv"
        if patches_csv.exists():
            df_patches = pd.read_csv(patches_csv)
            latest = df_patches[df_patches["Is_Latest"] == True]
            if not latest.empty:
                kb_ref = latest.iloc[0]["KB_Number"]

    print(f"🔑 KB Reference: {kb_ref}")
    print(f"\n🤖 Asking Gemini to find articles from major tech sources...\n")

    new_articles = fetch_articles(current_patch_date, kb_ref)

    if not new_articles:
        print("[EXIT] No articles returned.")
        sys.exit(0)

    # Load existing articles
    if ARTICLES_CSV.exists():
        df = pd.read_csv(ARTICLES_CSV)
        # Mark old articles as not current month
        df["Is_Current_Month"] = False
    else:
        df = pd.DataFrame()

    # Filter duplicates by title similarity
    existing_titles = [t.lower()[:50] for t in df["Title"].tolist()] if not df.empty else []
    new_rows = []
    for a in new_articles:
        title_key = a.get("Title", "").lower()[:50]
        if title_key not in existing_titles:
            new_rows.append(a)
            priority = a.get("Priority", "")
            icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")
            print(f"  {icon} [{priority}] {a.get('Title', '')[:60]}...")
        else:
            print(f"  [SKIP] Already exists: {a.get('Title', '')[:50]}")

        time.sleep(0.5)

    if not new_rows:
        print("\n[INFO] No new articles to add.")
        sys.exit(0)

    # Sort new articles by priority before adding
    new_rows.sort(key=lambda x: PRIORITY_ORDER.get(x.get("Priority", "Low"), 3))

    new_df = pd.DataFrame(new_rows)
    df = pd.concat([new_df, df], ignore_index=True)
    df.to_csv(ARTICLES_CSV, index=False)

    print(f"\n{'=' * 60}")
    print(f"✅ Added {len(new_rows)} new articles.")
    print(f"📊 Total articles: {len(df)}")

if __name__ == "__main__":
    run()
