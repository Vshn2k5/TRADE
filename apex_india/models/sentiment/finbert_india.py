"""
APEX INDIA — FinBERT India Sentiment Analyzer
================================================
NLP-based sentiment analysis for Indian financial news.
Falls back to keyword-based scoring if transformers unavailable.

Sources: MoneyControl, Economic Times, LiveMint headlines.

Usage:
    analyzer = FinBERTIndia()
    result = analyzer.analyze("HDFC Bank reports strong quarterly results")
"""

import re
from typing import Any, Dict, List, Optional

from apex_india.utils.logger import get_logger

logger = get_logger("models.sentiment")

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.info("transformers not installed — using keyword-based sentiment analyzer")


class FinBERTIndia:
    """
    Financial sentiment analysis optimized for Indian market news.
    """

    # India-specific financial keywords
    POSITIVE_KEYWORDS = [
        "bullish", "upgrade", "outperform", "buy", "strong", "beat",
        "growth", "profit", "recovery", "rally", "surge", "breakout",
        "robust", "dividend", "bonus", "target raised", "momentum",
        "expansion", "record high", "FII buying", "DII buying",
        "rate cut", "reform", "make in india", "PLI scheme",
        "exports rise", "GST collection", "PMI expansion",
        "manufacturing growth", "GDP growth", "rupee strengthens",
    ]

    NEGATIVE_KEYWORDS = [
        "bearish", "downgrade", "underperform", "sell", "weak", "miss",
        "loss", "decline", "crash", "plunge", "breakdown", "warning",
        "default", "scam", "fraud", "investigation", "ban", "penalty",
        "FII selling", "DII selling", "rate hike", "inflation",
        "recession", "stagflation", "rupee weakens", "trade deficit",
        "crude surge", "global slowdown", "geopolitical tension",
        "circuit breaker", "lower circuit", "frozen",
    ]

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.model_name = model_name
        self._pipeline = None
        self._is_loaded = False

        if HAS_TRANSFORMERS:
            try:
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=model_name,
                    tokenizer=model_name,
                    max_length=512,
                    truncation=True,
                )
                self._is_loaded = True
                logger.info(f"FinBERT loaded: {model_name}")
            except Exception as e:
                logger.warning(f"FinBERT load failed: {e} — using keyword fallback")

    # ───────────────────────────────────────────────────────────
    # Analyze Single Text
    # ───────────────────────────────────────────────────────────

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a financial text.

        Returns:
            {sentiment: str, score: float, method: str}
        """
        if not text or not text.strip():
            return {"sentiment": "neutral", "score": 0.0, "method": "empty"}

        if self._is_loaded and self._pipeline:
            return self._finbert_analyze(text)
        else:
            return self._keyword_analyze(text)

    def _finbert_analyze(self, text: str) -> Dict[str, Any]:
        """FinBERT transformer-based analysis."""
        try:
            result = self._pipeline(text[:512])[0]
            label = result["label"].lower()
            score = result["score"]

            # Normalize to [-1, 1]
            if label == "positive":
                normalized = score
            elif label == "negative":
                normalized = -score
            else:
                normalized = 0.0

            return {
                "sentiment": label,
                "score": round(normalized, 4),
                "confidence": round(score * 100, 1),
                "method": "finbert",
            }
        except Exception as e:
            return self._keyword_analyze(text)

    def _keyword_analyze(self, text: str) -> Dict[str, Any]:
        """Keyword-based fallback sentiment analysis."""
        text_lower = text.lower()

        pos_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text_lower)
        neg_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return {"sentiment": "neutral", "score": 0.0, "method": "keyword"}

        score = (pos_count - neg_count) / total

        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "confidence": round(abs(score) * 100, 1),
            "method": "keyword",
            "pos_matches": pos_count,
            "neg_matches": neg_count,
        }

    # ───────────────────────────────────────────────────────────
    # Batch Analysis
    # ───────────────────────────────────────────────────────────

    def analyze_headlines(
        self,
        headlines: List[str],
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze multiple headlines and produce aggregate sentiment.

        Args:
            headlines: List of news headline strings
            symbol: Optional stock symbol to filter relevance

        Returns:
            Aggregate sentiment with individual results
        """
        if not headlines:
            return {"aggregate_sentiment": "neutral", "score": 0.0, "n_headlines": 0}

        results = []
        for headline in headlines:
            result = self.analyze(headline)
            results.append(result)

        scores = [r["score"] for r in results]
        avg_score = sum(scores) / len(scores)

        if avg_score > 0.15:
            agg_sentiment = "positive"
        elif avg_score < -0.15:
            agg_sentiment = "negative"
        else:
            agg_sentiment = "neutral"

        return {
            "aggregate_sentiment": agg_sentiment,
            "score": round(avg_score, 4),
            "n_headlines": len(headlines),
            "positive_pct": round(sum(1 for r in results if r["sentiment"] == "positive") / len(results) * 100, 1),
            "negative_pct": round(sum(1 for r in results if r["sentiment"] == "negative") / len(results) * 100, 1),
            "neutral_pct": round(sum(1 for r in results if r["sentiment"] == "neutral") / len(results) * 100, 1),
            "top_positive": max(results, key=lambda x: x["score"]) if results else None,
            "top_negative": min(results, key=lambda x: x["score"]) if results else None,
        }
