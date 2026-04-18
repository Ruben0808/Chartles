# Chartles

Personal BSE/NSE research dashboard for Ruben Charles.

A research tool, not a price predictor. It scans Indian equities and mutual funds, surfaces chart patterns and technical/fundamental signals, and assigns each instrument a **health score** (Stable / Moderate / Cautious / Risky / Speculative). You decide; the dashboard makes you faster.

## Status

Phase 1 scaffolding — Nifty 50 scanner + static dashboard reading `data/stocks.json`.

## Stack

- **Scanner**: Python 3.11, `yfinance`, `pandas-ta`, `pandas` — no API keys, no paid services
- **Dashboard**: Next.js 14 static export on GitHub Pages
- **Scheduling**: GitHub Actions, nightly after NSE close (~4pm IST)
- **Data storage**: JSON files in `data/`, committed each scan

## Run locally

**Scanner:**

```bash
cd scanner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Outputs `../data/stocks.json`.

**Dashboard:**

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000.

## Known issues

- **yfinance can be rate-limited from residential IPs.** Yahoo sometimes returns an HTML block page instead of JSON, causing all symbols to fail. This typically resolves on its own, and works reliably from GitHub Actions' IP pool. If it persists locally, the next step is swapping to [`jugaad-data`](https://github.com/jugaad-py/jugaad-data) which hits NSE directly — will be added if the issue becomes chronic.

## Roadmap

- **Phase 1** (this) — Nifty 50 scanner, technical health score, static dashboard
- **Phase 2** — full NSE + liquid BSE + ETFs + MFs, fundamental overlay
- **Phase 3** — IPO Center (GMP aggregation, subscription status)
- **Phase 4** — portfolio tracker + budget allocator (localStorage)
- **Phase 5** — news + FinBERT sentiment
- **Phase 6** — chart pattern detection + backtester + alerts
