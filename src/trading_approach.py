import math
from abc import ABC, abstractmethod
import config

class TradingApproach(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the identifier name of the approach."""
        pass

    @abstractmethod
    def get_max_risk_pct(self) -> float:
        """Returns the maximum proportion of equity to risk as margin."""
        pass

    @abstractmethod
    def calculate_position_size(self, max_possible_contracts: int, confidence: float) -> int:
        """Calculates target contracts based on the strategy logic."""
        pass

    @abstractmethod
    def get_trade_confidence_threshold(self) -> float:
        """Returns the minimum confidence score required to enter a trade."""
        pass

    @abstractmethod
    def adjust_prompt_instructions(self) -> str:
        """Returns stance-specific instructions to be injected into the master prompt."""
        pass


class BalancedApproach(TradingApproach):
    @property
    def name(self) -> str:
        return "Balanced"

    def get_max_risk_pct(self) -> float:
        return getattr(config, 'MAX_RISK_PCT', 0.20)

    def calculate_position_size(self, max_possible_contracts: int, confidence: float) -> int:
        # Linear scaling based on confidence
        return math.floor(max_possible_contracts * (confidence / 100.0))

    def get_trade_confidence_threshold(self) -> float:
        return 0.0

    def adjust_prompt_instructions(self) -> str:
        # Balanced does not inject any additional instructions to preserve the exact original prompt
        return ""


class AggressiveApproach(TradingApproach):
    @property
    def name(self) -> str:
        return "Aggressive"

    def get_max_risk_pct(self) -> float:
        return 0.40  # Risk limit is doubled (40% of equity)

    def calculate_position_size(self, max_possible_contracts: int, confidence: float) -> int:
        # Scale aggressively using square root of confidence
        return math.floor(max_possible_contracts * math.sqrt(confidence / 100.0))

    def get_trade_confidence_threshold(self) -> float:
        return 0.0

    def adjust_prompt_instructions(self) -> str:
        return "You have a high risk tolerance. When you see strong trends or clear macro-directional indicators, act aggressively and decisively with high confidence. Do not be overly concerned with short-term noise or minor counter-trends. Assign higher confidence scores to capture larger position sizes."


class ConservativeApproach(TradingApproach):
    @property
    def name(self) -> str:
        return "Conservative"

    def get_max_risk_pct(self) -> float:
        return 0.10  # Risk limit is halved (10% of equity)

    def calculate_position_size(self, max_possible_contracts: int, confidence: float) -> int:
        # Scale defensively using squared confidence
        return math.floor(max_possible_contracts * ((confidence / 100.0) ** 2))

    def get_trade_confidence_threshold(self) -> float:
        return 55.0  # Avoid execution on low-confidence setups

    def adjust_prompt_instructions(self) -> str:
        return "You are highly risk-averse. Prioritize capital preservation above all. If you are currently FLAT, output HOLD to stay in cash. If you are currently in a position, output HOLD only if conviction remains. Only enter a new LONG or SHORT when certainty is extremely high. Reflect this by assigning lower confidence scores unless you are extremely certain."

class TechnicalAnalysisApproach(TradingApproach):
    @property
    def name(self) -> str:
        return "TechnicalAnalysis"

    def get_max_risk_pct(self) -> float:
        return 0.25  # Between Balanced (0.20) and Aggressive (0.40)

    def calculate_position_size(self, max_possible_contracts: int, confidence: float) -> int:
        # Linear scaling (same as Balanced) for fair prompt-vs-prompt comparison
        return math.floor(max_possible_contracts * (confidence / 100.0))

    def get_trade_confidence_threshold(self) -> float:
        return 0.0

    def adjust_prompt_instructions(self) -> str:
        return (
            "You are operating in TECHNICAL ANALYSIS mode. Think like a quantitative portfolio manager.\n\n"
            "DECISION FRAMEWORK (follow this exact hierarchy):\n"
            "  STEP 1 — FUNDAMENTAL THESIS (Primary): Read the macroeconomic news and individual stock headlines. "
            "Form your directional thesis (bullish / bearish / neutral) based PURELY on news sentiment and "
            "macro context. This is your PRIMARY signal. Without a clear fundamental thesis, default to HOLD.\n\n"
            "  STEP 2 — TECHNICAL CONFIRMATION (Secondary): Examine the Composite Technical Regime score "
            "and the individual indicator votes (RSI, SMA trend, MACD, Bollinger, Momentum). "
            "Use these as CONFIRMATION or REJECTION of your fundamental thesis. "
            "No single indicator should override the news-driven thesis on its own.\n\n"
            "  STEP 3 — CONFLUENCE-BASED CONFIDENCE CALIBRATION:\n"
            "    • News bullish + Technicals STRONG BULLISH (score ≥ +3) → High confidence (75-90)\n"
            "    • News bullish + Technicals LEAN BULLISH (score +1 to +2) → Moderate confidence (55-70)\n"
            "    • News bullish + Technicals NEUTRAL/MIXED (score 0) → Low confidence (40-55), consider HOLD\n"
            "    • News bullish + Technicals BEARISH (score < 0) → CONFLICT → output HOLD or very low confidence (25-40)\n"
            "    • News bearish + Technicals confirm bearish → Mirror the above for SHORT decisions\n"
            "    • News neutral + any technicals → HOLD unless composite score is extreme (|score| ≥ 4)\n\n"
            "CRITICAL RULES:\n"
            "  - A single overbought RSI does NOT mean 'sell'. A single SMA crossover does NOT mean 'buy'. "
            "Only CONFLUENCE of multiple signals matters.\n"
            "  - If fundamental and technical signals CONFLICT, always reduce confidence or output HOLD. "
            "Never take a high-conviction trade against your own fundamental thesis.\n"
            "  - Treat the Composite Technical Regime score as a pre-computed summary. "
            "A net score of 0 or ±1 means the technicals are inconclusive — rely more heavily on news.\n"
            "  - You are benchmarked on risk-adjusted returns. Avoiding bad trades is as valuable as finding good ones."
        )


class TradingApproachFactory:
    _approaches = {
        "balanced": BalancedApproach(),
        "aggressive": AggressiveApproach(),
        "conservative": ConservativeApproach(),
        "technicalanalysis": TechnicalAnalysisApproach(),
        "v1": BalancedApproach()  # Map legacy results to Balanced to preserve historical behaviors
    }

    @classmethod
    def get_approach(cls, name: str) -> TradingApproach:
        if not name:
            return cls._approaches["balanced"]
        cleaned_name = str(name).lower().strip()
        return cls._approaches.get(cleaned_name, cls._approaches["balanced"])

