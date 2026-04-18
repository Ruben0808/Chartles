"""
Chartles Phase 1 scanner.

Pulls 1y of OHLCV for each symbol in universe/nifty50.txt via jugaad-data
(direct NSE access, no API keys, no Yahoo dependency), computes a technical
health score, writes ../data/stocks.json.
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Enforce a default timeout on every HTTP GET — jugaad-data doesn't set one,
# and a hung socket against NSE otherwise freezes the scanner indefinitely.
_original_session_get = requests.Session.get
def _session_get_with_timeout(self, url, **kwargs):
    kwargs.setdefault("timeout", 15)
    return _original_session_get(self, url, **kwargs)
requests.Session.get = _session_get_with_timeout  # type: ignore[method-assign]

from jugaad_data.nse import stock_df  # noqa: E402  (imported after monkey-patch)

SCANNER_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCANNER_DIR.parent
UNIVERSE_FILE = SCANNER_DIR / "universe" / "nifty50.txt"
OUT_FILE = REPO_ROOT / "data" / "stocks.json"

# jugaad-data has a cache-dir race in its thread pool (os.makedirs without exist_ok).
# Pre-create the dirs so all worker threads find them already present.
for _cache in ("nsehistory-stock", "nsehistory-index"):
    (Path.home() / "Library" / "Caches" / _cache).mkdir(parents=True, exist_ok=True)
    (Path.home() / ".cache" / _cache).mkdir(parents=True, exist_ok=True)

TIERS = [
    (80, "Stable"),
    (65, "Moderate"),
    (50, "Cautious"),
    (35, "Risky"),
    (0, "Speculative"),
]


@dataclass
class StockRow:
    symbol: str
    name: str
    price: float
    change_1d_pct: float
    change_1y_pct: float
    rsi_14: float
    sma_50: float
    sma_200: float
    above_200dma: bool
    dist_from_52w_high_pct: float
    max_drawdown_1y_pct: float
    volatility_1y_pct: float
    avg_daily_value_cr: float
    score: int
    tier: str
    reasons: list[str]


def load_universe() -> list[str]:
    return [s.strip() for s in UNIVERSE_FILE.read_text().splitlines() if s.strip()]


def _fetch_inner(symbol: str) -> pd.DataFrame | None:
    end = date.today()
    start = end - timedelta(days=400)
    df = stock_df(symbol=symbol, from_date=start, to_date=end, series="EQ")
    if df is None or df.empty or len(df) < 60:
        return None
    df = df.rename(
        columns={
            "OPEN": "Open",
            "HIGH": "High",
            "LOW": "Low",
            "CLOSE": "Close",
            "VOLUME": "Volume",
        }
    )
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.sort_values("DATE").reset_index(drop=True)
    return df[["DATE", "Open", "High", "Low", "Close", "Volume"]].set_index("DATE")


def fetch_ohlcv(symbol: str, overall_timeout_s: int = 45) -> pd.DataFrame | None:
    """Fetch with an overall per-symbol timeout. jugaad-data spawns its own
    thread pool internally, and even with request-level timeouts the whole
    operation can stall on chunk coordination — this outer watchdog bounds it."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_fetch_inner, symbol)
        try:
            return future.result(timeout=overall_timeout_s)
        except concurrent.futures.TimeoutError:
            print(f"  timeout fetching {symbol}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  fetch failed for {symbol}: {e}", file=sys.stderr)
            return None


def tier_for(score: int) -> str:
    for threshold, label in TIERS:
        if score >= threshold:
            return label
    return "Speculative"


def score_stock(symbol: str, df: pd.DataFrame) -> StockRow | None:
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    volume = df["Volume"].astype(float)

    if len(close) < 60:
        return None

    price = float(close.iloc[-1])
    change_1d_pct = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) >= 2 else 0.0
    change_1y_pct = float((close.iloc[-1] / close.iloc[0] - 1) * 100)

    sma_50 = float(close.tail(50).mean()) if len(close) >= 50 else float(close.mean())
    sma_200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())
    above_200dma = price > sma_200

    high_52w = float(close.max())
    dist_from_high = float((price / high_52w - 1) * 100)

    cum_max = close.cummax()
    drawdown = (close / cum_max - 1) * 100
    max_drawdown = float(drawdown.min())

    daily_returns = close.pct_change().dropna()
    volatility = float(daily_returns.std() * np.sqrt(252) * 100) if len(daily_returns) > 1 else 0.0

    rsi = compute_rsi(close, 14)
    rsi_14 = float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else 50.0

    avg_daily_value_cr = float((close * volume).tail(30).mean() / 1e7) if len(close) >= 30 else 0.0

    score, reasons = compute_score(
        above_200dma=above_200dma,
        dist_from_high=dist_from_high,
        rsi=rsi_14,
        volatility=volatility,
        max_drawdown=max_drawdown,
        avg_daily_value_cr=avg_daily_value_cr,
        change_1y_pct=change_1y_pct,
    )

    return StockRow(
        symbol=symbol,
        name=symbol,
        price=round(price, 2),
        change_1d_pct=round(change_1d_pct, 2),
        change_1y_pct=round(change_1y_pct, 2),
        rsi_14=round(rsi_14, 1),
        sma_50=round(sma_50, 2),
        sma_200=round(sma_200, 2),
        above_200dma=above_200dma,
        dist_from_52w_high_pct=round(dist_from_high, 2),
        max_drawdown_1y_pct=round(max_drawdown, 2),
        volatility_1y_pct=round(volatility, 2),
        avg_daily_value_cr=round(avg_daily_value_cr, 2),
        score=score,
        tier=tier_for(score),
        reasons=reasons,
    )


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_score(
    *,
    above_200dma: bool,
    dist_from_high: float,
    rsi: float,
    volatility: float,
    max_drawdown: float,
    avg_daily_value_cr: float,
    change_1y_pct: float,
) -> tuple[int, list[str]]:
    """
    Phase 1 uses technical posture (40%) + volatility (30%) + liquidity (15%)
    + momentum (15%). Fundamentals come in Phase 2.
    """
    reasons: list[str] = []

    # Technical posture: above 200-DMA and not extended from 52w high is healthiest.
    tech = 0
    if above_200dma:
        tech += 25
        reasons.append("Above 200-DMA")
    else:
        reasons.append("Below 200-DMA")
    if -10 <= dist_from_high <= 0:
        tech += 10
    elif dist_from_high < -30:
        tech -= 5
        reasons.append(f"{abs(dist_from_high):.0f}% off 52w high")
    if 40 <= rsi <= 65:
        tech += 5
    elif rsi > 75:
        reasons.append("RSI overbought")
    elif rsi < 30:
        reasons.append("RSI oversold")

    # Volatility: annualized daily-return stdev. Lower is more stable.
    if volatility < 20:
        vol_component = 30
    elif volatility < 30:
        vol_component = 22
    elif volatility < 45:
        vol_component = 14
    else:
        vol_component = 5
        reasons.append(f"High volatility ({volatility:.0f}%)")

    # Drawdown pressure
    dd_penalty = 0
    if max_drawdown < -40:
        dd_penalty = 10
        reasons.append(f"Deep 1y drawdown ({max_drawdown:.0f}%)")
    elif max_drawdown < -25:
        dd_penalty = 5

    # Liquidity: avg daily traded value in crores.
    if avg_daily_value_cr > 100:
        liq = 15
    elif avg_daily_value_cr > 25:
        liq = 11
    elif avg_daily_value_cr > 5:
        liq = 7
    else:
        liq = 3
        reasons.append("Low liquidity")

    # Momentum (1y return)
    if change_1y_pct > 25:
        mom = 15
    elif change_1y_pct > 0:
        mom = 10
    elif change_1y_pct > -15:
        mom = 5
    else:
        mom = 0
        reasons.append(f"Negative 1y return ({change_1y_pct:.0f}%)")

    score = tech + vol_component + liq + mom - dd_penalty
    score = max(0, min(100, score))
    return score, reasons


def main() -> int:
    symbols = load_universe()
    print(f"scanning {len(symbols)} symbols...")

    rows: list[dict] = []
    failed: list[str] = []

    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym}")
        df = fetch_ohlcv(sym)
        if df is None:
            failed.append(sym)
            continue
        row = score_stock(sym, df)
        if row is None:
            failed.append(sym)
            continue
        rows.append(asdict(row))
        time.sleep(0.4)  # be polite to yfinance/Yahoo

    rows.sort(key=lambda r: r["score"], reverse=True)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": "nifty50",
        "count": len(rows),
        "failed": failed,
        "stocks": rows,
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2))
    print(f"\nwrote {OUT_FILE} ({len(rows)} stocks, {len(failed)} failed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
