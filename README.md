# Windows Patch Intelligence 🛡️

> AI-powered Windows 11 Patch Tuesday tracker. Automatically fetches KB numbers, CVE counts, build versions and curated security news every month.

## 🌐 Live Site
**[patchtuesday.webline.cloud](https://patchtuesday.webline.cloud)**

---

## What It Does

- 📅 **Detects Patch Tuesday** automatically (2nd Tuesday of every month)
- 🛡️ **Fetches KB numbers** and Windows 11 build versions via Gemini AI
- 📰 **Curates news articles** from BleepingComputer, The Verge, Ars Technica, Windows Central and more
- ⏱️ **Counts down** days since last patch and days until next
- 🔄 **Rotates automatically** — new month's patches go to top, old ones move to history

## Project Structure

```
/
├── data/
│   ├── patches.csv       ← KB numbers, versions, CVE counts (auto-updated)
│   ├── articles.csv      ← AI-curated news articles (auto-updated)
│   └── meta.json         ← Patch dates, countdown, news window status
├── public/
│   └── index.html        ← Dashboard (served by GitHub Pages)
├── scripts/
│   ├── fetch_patches.py  ← Gemini AI patch data fetcher
│   ├── fetch_articles.py ← Gemini AI news article fetcher
│   └── requirements.txt
└── .github/workflows/
    ├── patch_tuesday.yml ← Runs on Patch Tuesday
    └── daily_news.yml    ← Runs daily (active 7 days after patch)
```

## Setup

### 1. Fork & Clone
```bash
git clone https://github.com/navneet-20/windows-patch-intelligence.git
cd windows-patch-intelligence
```

### 2. Enable GitHub Pages
Settings → Pages → Branch: `main` → Folder: `/public`

### 3. Add API Secret
Settings → Secrets → Actions → New secret:
- Name: `GEMINI_API_KEY`
- Value: Your Gemini API key from [aistudio.google.com](https://aistudio.google.com/apikey)

### 4. Test It
Actions → "Fetch Patch Tuesday Data" → Run workflow

---

## How the Automation Works

```
2nd Tuesday of each month (20:00 UTC)
        ↓
fetch_patches.py runs via GitHub Actions
        ↓
Gemini fetches KB numbers + CVE counts + versions
        ↓
patches.csv + meta.json updated

Then daily for 7 days:
        ↓
fetch_articles.py runs
        ↓
Gemini curates news from major tech sources
        ↓
articles.csv updated, sorted by priority
        ↓
Site auto-refreshes via GitHub Pages
```

---

## Built by
**Navneet Kumar** — [github.com/navneet-20](https://github.com/navneet-20)

Also check out: [IsItFree?](https://isitfree.webline.cloud) — Software license directory

---

## Disclaimer
Patch data is AI-verified. Always confirm KB details on the [Microsoft Security Update Guide](https://msrc.microsoft.com/update-guide) before deploying in production.
