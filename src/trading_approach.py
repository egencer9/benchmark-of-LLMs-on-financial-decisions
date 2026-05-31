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


class TradingApproachFactory:
    _approaches = {
        "balanced": BalancedApproach(),
        "aggressive": AggressiveApproach(),
        "conservative": ConservativeApproach(),
        "v1": BalancedApproach()  # Map legacy results to Balanced to preserve historical behaviors
    }

    @classmethod
    def get_approach(cls, name: str) -> TradingApproach:
        if not name:
            return cls._approaches["balanced"]
        cleaned_name = str(name).lower().strip()
        return cls._approaches.get(cleaned_name, cls._approaches["balanced"])
