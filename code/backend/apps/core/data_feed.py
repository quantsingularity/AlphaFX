"""
AlphaFX Data Feed Service
Live exchange rates, OHLCV history, economic calendar.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
import numpy as np
import pandas as pd
from apps.core.pricing import FALLBACK_RATES, pip_size, spread_pips
from django.conf import settings
from django.core.cache import cache

# ─── Live rate fetching ────────────────────────────────────────────────────────


async def fetch_live_rates(base: str = "USD") -> dict[str, float]:
    """
    Fetch live rates from ExchangeRate-API.
    Falls back to static matrix if key is missing or request fails.
    """
    api_key = getattr(settings, "EXCHANGERATE_API_KEY", "")
    cache_key = f"live_rates:{base.upper()}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    if api_key:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                rates = data.get("conversion_rates", {})
                if rates:
                    cache.set(cache_key, rates, timeout=60)
                    return rates
        except Exception:
            pass

    rates = _fallback_rates_from_base(base)
    cache.set(cache_key, rates, timeout=30)
    return rates


def _fallback_rates_from_base(base: str) -> dict[str, float]:
    """Convert fallback matrix to base-currency-relative rates."""
    base = base.upper()
    usd_rates = {
        "USD": 1.0,
        "EUR": 0.9224,
        "GBP": 0.7902,
        "JPY": 154.32,
        "CHF": 0.9012,
        "AUD": 1.5330,
        "NZD": 1.6706,
        "CAD": 1.3654,
        "SGD": 1.3421,
        "HKD": 7.8213,
        "MXN": 17.2345,
        "ZAR": 18.7654,
        "TRY": 32.1456,
        "NOK": 10.75,
        "SEK": 10.55,
    }
    if base in usd_rates:
        base_rate = usd_rates[base]
        return {ccy: round(r / base_rate, 6) for ccy, r in usd_rates.items()}
    return usd_rates


# ─── Pair quote builder ────────────────────────────────────────────────────────


async def build_pair_quotes(pairs: list[str]) -> list[dict]:
    """Build bid/ask/mid quotes for a list of pairs."""
    now = datetime.now(timezone.utc)
    quotes = []

    for pair in pairs:
        pair = pair.upper()
        if len(pair) != 6:
            continue

        spot = FALLBACK_RATES.get(pair, 1.0)
        sp = spread_pips(pair)
        ps = pip_size(pair)
        half = sp * ps / 2

        quotes.append(
            {
                "base": pair[:3],
                "quote": pair[3:],
                "bid": round(spot - half, 5),
                "ask": round(spot + half, 5),
                "mid": round(spot, 5),
                "spread_pips": sp,
                "timestamp": now.isoformat(),
                "source": "synthetic",
            }
        )

    return quotes


# ─── OHLCV history ────────────────────────────────────────────────────────────


async def fetch_fx_history(
    pair: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    n_days: int = 252,
) -> pd.DataFrame:
    """
    Fetch OHLCV history: tries yfinance, falls back to synthetic GBM.
    """
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=n_days))

    try:
        import yfinance as yf

        ticker = f"{pair[:3]}{pair[3:]}=X" if len(pair) == 6 else f"{pair}=X"
        data = yf.download(
            ticker, start=start.isoformat(), end=end.isoformat(), progress=False
        )
        if not data.empty:
            cols = {
                c.lower() if isinstance(c, str) else c[0].lower(): c
                for c in data.columns
            }
            close_col = cols.get("close") or cols.get("adj close")
            if close_col is not None:
                df = data[[close_col]].rename(columns={close_col: "close"})
                df.index = pd.to_datetime(df.index)
                return df
    except Exception:
        pass

    return _synthetic_history(pair, start, end)


def _synthetic_history(pair: str, start: date, end: date) -> pd.DataFrame:
    """Generate synthetic OHLCV from GBM for the date range."""
    base_price = FALLBACK_RATES.get(pair.upper(), 1.0)
    dates = pd.date_range(start=start, end=end, freq="B")
    n = len(dates)
    rng = np.random.default_rng(abs(hash(pair)) % (2**31))
    rets = rng.normal(0.00005, 0.006, n)
    closes = base_price * np.exp(np.cumsum(rets))
    return pd.DataFrame({"close": closes}, index=dates)


# ─── Economic calendar ────────────────────────────────────────────────────────


def economic_calendar() -> list[dict]:
    """
    Return a rolling 5-day economic calendar with representative high-impact events.
    """
    today = date.today()
    events = [
        # Today
        {
            "date": str(today),
            "time": "08:30",
            "currency": "USD",
            "event": "US CPI MoM",
            "impact": "high",
            "forecast": "0.3%",
            "previous": "0.2%",
            "actual": None,
        },
        {
            "date": str(today),
            "time": "10:00",
            "currency": "USD",
            "event": "US Retail Sales",
            "impact": "high",
            "forecast": "0.4%",
            "previous": "0.1%",
            "actual": None,
        },
        # +1 day
        {
            "date": str(today + timedelta(days=1)),
            "time": "07:00",
            "currency": "GBP",
            "event": "UK GDP MoM",
            "impact": "high",
            "forecast": "0.1%",
            "previous": "0.0%",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=1)),
            "time": "09:30",
            "currency": "EUR",
            "event": "ECB Meeting Minutes",
            "impact": "high",
            "forecast": "—",
            "previous": "—",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=1)),
            "time": "14:00",
            "currency": "USD",
            "event": "US Building Permits",
            "impact": "medium",
            "forecast": "1.45M",
            "previous": "1.43M",
            "actual": None,
        },
        # +2 days
        {
            "date": str(today + timedelta(days=2)),
            "time": "00:30",
            "currency": "JPY",
            "event": "Japan CPI YoY",
            "impact": "medium",
            "forecast": "2.5%",
            "previous": "2.7%",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=2)),
            "time": "12:30",
            "currency": "CAD",
            "event": "BoC Rate Decision",
            "impact": "high",
            "forecast": "4.75%",
            "previous": "4.75%",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=2)),
            "time": "19:00",
            "currency": "USD",
            "event": "FOMC Minutes",
            "impact": "high",
            "forecast": "—",
            "previous": "—",
            "actual": None,
        },
        # +3 days
        {
            "date": str(today + timedelta(days=3)),
            "time": "08:30",
            "currency": "USD",
            "event": "US Nonfarm Payrolls",
            "impact": "high",
            "forecast": "175K",
            "previous": "187K",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=3)),
            "time": "08:30",
            "currency": "USD",
            "event": "US Unemployment Rate",
            "impact": "high",
            "forecast": "3.9%",
            "previous": "3.9%",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=3)),
            "time": "10:00",
            "currency": "EUR",
            "event": "EU CPI Flash YoY",
            "impact": "high",
            "forecast": "2.4%",
            "previous": "2.6%",
            "actual": None,
        },
        # +4 days
        {
            "date": str(today + timedelta(days=4)),
            "time": "01:30",
            "currency": "AUD",
            "event": "RBA Rate Decision",
            "impact": "high",
            "forecast": "4.35%",
            "previous": "4.35%",
            "actual": None,
        },
        {
            "date": str(today + timedelta(days=4)),
            "time": "13:30",
            "currency": "GBP",
            "event": "UK CPI YoY",
            "impact": "high",
            "forecast": "3.1%",
            "previous": "3.4%",
            "actual": None,
        },
    ]
    return events
