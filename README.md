# Delhi Gold Price Tracker

Tracks 24K / 22K / 18K gold rates in Delhi, computes a daily buy/wait signal from price
action, and pushes alerts to Telegram. Runs entirely on free GitHub infrastructure —
GitHub Actions for the twice-daily fetch, GitHub Pages for the dashboard.

**Dashboard:** `https://<your-github-username>.github.io/gold-tracker/` (enable after first push)

## How it works

1. A GitHub Actions workflow runs twice a day (~09:15 and ~18:15 IST).
2. It scrapes Delhi gold rates from goodreturns.in (primary — all 3 karats, plus a
   10-day history table used to seed data on first run), with policybazaar.com and
   business-standard.com as cross-checks, plus international spot (goldprice.dev) as
   a sanity/premium canary and USD/INR (frankfurter.dev) for context.
3. Prices are reconciled (median, outlier rejection) and appended to `docs/data/history.json`
   (lives under `docs/` so GitHub Pages — which only serves that folder — can read it directly).
4. `src/signal.py` computes a deterministic BUY / ACCUMULATE / WAIT / HOLD verdict from
   moving averages, 30-day range position, and down-streaks — no LLM, no API cost.
5. Telegram gets a daily digest (rates + verdict + true jewellery cost) and an
   immediate dip alert when a real drop fires.
6. `docs/index.html` reads the committed JSON and renders a dashboard; GitHub Pages
   serves it as a free public URL that updates on every run.

## Setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) → get a bot token.
2. Message your bot once, then get your chat ID from
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. In this repo's Settings → Secrets and variables → Actions, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Settings → Pages → Source: Deploy from a branch → Branch `main`, folder `/docs`.
5. Actions tab → run "Track Gold Prices" once manually (`workflow_dispatch`) to seed data.

## Local development

```
pip install -r requirements.txt
python -m src.tracker --dry-run
```

Local runs read `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` from `C:\credentials\.env`
(via python-dotenv, absolute path) — never from a project-local `.env`.

## WhatsApp

Not in V1. Business-initiated WhatsApp alerts require a Meta-approved utility template
and are billed per message once outside the free 24h service window (which Meta is
ending in Oct 2026); the Twilio sandbox alternative expires every 72 hours, unsuitable
for a standing daily alert. `src/notifiers/whatsapp.py` is a stub — implement it and
register it in `src/config.py` when you're ready to pay for/maintain that channel.

## Known limitations

- Scraped city rates track published city averages, not any specific jeweller's
  quote, and exclude making charges (the dashboard's true-cost estimator adds these
  back using a configurable making-charge %).
- Source sites can change their HTML; `src/reconcile.py` guards against a single
  broken scraper skewing the headline number, and stale data is carried forward
  (never invented) with a `stale` flag.
