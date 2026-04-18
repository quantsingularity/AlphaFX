"""
AlphaFX AI Services - FX Sentiment Analyser
Analyses news headlines and economic commentary for FX-relevant
bullish / bearish / neutral sentiment using FinBERT.

Provides:
  - Per-headline sentiment score
  - Aggregated currency sentiment (net bullish score per CCY)
  - Macro sentiment index across G10 currencies

Falls back to rule-based lexicon scoring when transformers or
a network connection are unavailable.

Usage:
  from ai_services.services.sentiment import SentimentService
  svc = SentimentService()
  result = svc.analyse_headline("Fed signals further rate hikes as inflation persists")
  print(result)
  # {"label": "BULLISH_USD", "score": 0.87, "positive": 0.87, "negative": 0.05, "neutral": 0.08}
"""

# ---------------------------------------------------------------------------
# Rule-based fallback lexicon (used when FinBERT unavailable)
# ---------------------------------------------------------------------------

_BULLISH_KEYWORDS = {
    "rate hike",
    "hawkish",
    "tightening",
    "strong gdp",
    "beat expectations",
    "above forecast",
    "robust growth",
    "record high",
    "rate increase",
    "inflation rises",
    "hike rates",
    "aggressive tightening",
    "hot cpi",
    "strong jobs",
    "nfp beat",
    "trade surplus",
}

_BEARISH_KEYWORDS = {
    "rate cut",
    "dovish",
    "easing",
    "recession",
    "gdp miss",
    "below forecast",
    "slow growth",
    "contraction",
    "deflation",
    "unemployment rises",
    "trade deficit",
    "fiscal deficit",
    "debt ceiling",
    "banking crisis",
    "flash crash",
    "emergency cut",
    "quantitative easing",
    "risk off",
}

_CCY_MENTIONS = {
    "USD": ["dollar", "usd", "fed", "fomc", "powell", "us economy", "america"],
    "EUR": ["euro", "eur", "ecb", "lagarde", "eurozone", "europe"],
    "GBP": [
        "pound",
        "gbp",
        "boe",
        "bank of england",
        "bailey",
        "uk economy",
        "britain",
    ],
    "JPY": ["yen", "jpy", "boj", "bank of japan", "ueda", "japan"],
    "AUD": ["aussie", "aud", "rba", "reserve bank australia", "australia"],
    "NZD": ["kiwi", "nzd", "rbnz", "new zealand"],
    "CAD": ["loonie", "cad", "boc", "bank of canada", "canada", "oil price"],
    "CHF": ["franc", "chf", "snb", "swiss", "switzerland"],
    "NOK": ["krone", "nok", "norges bank", "norway", "oil"],
    "SEK": ["krona", "sek", "riksbank", "sweden"],
}


def _rule_based_score(text: str) -> dict:
    """Lexicon-based fallback sentiment scorer."""
    text_lower = text.lower()
    bull_hits = sum(1 for kw in _BULLISH_KEYWORDS if kw in text_lower)
    bear_hits = sum(1 for kw in _BEARISH_KEYWORDS if kw in text_lower)
    total = bull_hits + bear_hits + 1e-9

    pos = bull_hits / total
    neg = bear_hits / total
    neu = max(0.0, 1.0 - pos - neg)

    if pos > 0.5:
        label = "POSITIVE"
    elif neg > 0.5:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    return {
        "label": label,
        "score": round(max(pos, neg), 3),
        "positive": round(pos, 3),
        "negative": round(neg, 3),
        "neutral": round(neu, 3),
        "source": "lexicon",
    }


def _detect_currencies(text: str) -> list[str]:
    """Return list of currency codes mentioned in text."""
    text_lower = text.lower()
    detected = []
    for ccy, terms in _CCY_MENTIONS.items():
        if any(t in text_lower for t in terms):
            detected.append(ccy)
    return detected


# ---------------------------------------------------------------------------
# Sentiment service
# ---------------------------------------------------------------------------


class SentimentService:
    """
    FX news sentiment service.

    Attempts to load ProsusAI/finbert (transformers) for state-of-the-art
    financial sentiment. Falls back to the rule-based lexicon scorer when
    the model or network is unavailable.
    """

    def __init__(self, model_name: str = "ProsusAI/finbert", use_gpu: bool = False):
        self.model_name = model_name
        self.use_gpu = use_gpu
        self._pipeline = None
        self._loaded = False
        self._try_load()

    def _try_load(self) -> None:
        try:
            from transformers import pipeline

            device = 0 if self.use_gpu else -1
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                device=device,
                top_k=None,
            )
            self._loaded = True
        except Exception:
            self._loaded = False

    # ---- Single headline ---------------------------------------------------

    def analyse_headline(self, text: str) -> dict:
        """
        Analyse a single news headline.

        Returns dict with keys:
          label     - POSITIVE / NEGATIVE / NEUTRAL
          score     - confidence of the dominant label
          positive  - positive probability
          negative  - negative probability
          neutral   - neutral probability
          currencies - list of detected currency codes
          source    - "finbert" or "lexicon"
        """
        currencies = _detect_currencies(text)

        if self._loaded and self._pipeline is not None:
            try:
                raw = self._pipeline(text[:512])[0]
                scores = {item["label"].lower(): item["score"] for item in raw}
                pos = scores.get("positive", 0.0)
                neg = scores.get("negative", 0.0)
                neu = scores.get("neutral", 0.0)

                if pos >= neg and pos >= neu:
                    label, score = "POSITIVE", pos
                elif neg >= pos and neg >= neu:
                    label, score = "NEGATIVE", neg
                else:
                    label, score = "NEUTRAL", neu

                return {
                    "label": label,
                    "score": round(score, 4),
                    "positive": round(pos, 4),
                    "negative": round(neg, 4),
                    "neutral": round(neu, 4),
                    "currencies": currencies,
                    "source": "finbert",
                }
            except Exception:
                pass

        result = _rule_based_score(text)
        result["currencies"] = currencies
        return result

    # ---- Batch headlines ---------------------------------------------------

    def analyse_batch(self, headlines: list[str]) -> list[dict]:
        """Analyse a list of headlines and return per-item results."""
        return [self.analyse_headline(h) for h in headlines]

    # ---- Currency sentiment aggregation ------------------------------------

    def aggregate_currency_sentiment(
        self,
        headlines: list[str],
    ) -> dict[str, dict]:
        """
        Compute net sentiment score per currency from a batch of headlines.

        Returns dict keyed by CCY code with:
          net_score     - mean(positive - negative) for headlines mentioning this CCY
          count         - number of relevant headlines
          bullish_count - headlines with positive label
          bearish_count - headlines with negative label
          signal        - BULLISH / BEARISH / NEUTRAL
        """
        analysed = self.analyse_batch(headlines)

        ccy_data: dict[str, list[float]] = {}
        ccy_labels: dict[str, list[str]] = {}

        for item in analysed:
            net = item["positive"] - item["negative"]
            for ccy in item.get("currencies", []):
                ccy_data.setdefault(ccy, []).append(net)
                ccy_labels.setdefault(ccy, []).append(item["label"])

        result = {}
        for ccy, scores in ccy_data.items():
            labels = ccy_labels[ccy]
            net_score = sum(scores) / len(scores)
            bull_count = labels.count("POSITIVE")
            bear_count = labels.count("NEGATIVE")

            if net_score > 0.1:
                signal = "BULLISH"
            elif net_score < -0.1:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            result[ccy] = {
                "net_score": round(net_score, 4),
                "count": len(scores),
                "bullish_count": bull_count,
                "bearish_count": bear_count,
                "signal": signal,
            }

        return result

    # ---- Macro sentiment index --------------------------------------------

    def macro_sentiment_index(self, headlines: list[str]) -> dict:
        """
        Compute an overall risk-on / risk-off sentiment index from headlines.
        Positive index -> risk-on (USD weak, risk FX strong)
        Negative index -> risk-off (USD strong, JPY/CHF bid)

        Returns score in [-1, +1].
        """
        if not headlines:
            return {"index": 0.0, "regime": "NEUTRAL", "sample_size": 0}

        analysed = self.analyse_batch(headlines)
        scores = [item["positive"] - item["negative"] for item in analysed]
        index = sum(scores) / len(scores)

        regime = (
            "RISK_ON" if index > 0.15 else "RISK_OFF" if index < -0.15 else "NEUTRAL"
        )

        return {
            "index": round(index, 4),
            "regime": regime,
            "sample_size": len(headlines),
            "bullish_pct": round(
                sum(1 for s in scores if s > 0) / len(scores) * 100, 1
            ),
            "bearish_pct": round(
                sum(1 for s in scores if s < 0) / len(scores) * 100, 1
            ),
        }
