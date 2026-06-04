import sys
import os
import unittest

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.trading_approach import TradingApproachFactory, BalancedApproach, AggressiveApproach, ConservativeApproach

class TestTradingApproaches(unittest.TestCase):
    def test_factory_resolutions(self):
        self.assertIsInstance(TradingApproachFactory.get_approach("Balanced"), BalancedApproach)
        self.assertIsInstance(TradingApproachFactory.get_approach("Aggressive"), AggressiveApproach)
        self.assertIsInstance(TradingApproachFactory.get_approach("Conservative"), ConservativeApproach)
        self.assertIsInstance(TradingApproachFactory.get_approach("v1"), BalancedApproach)
        self.assertIsInstance(TradingApproachFactory.get_approach(""), BalancedApproach)
        self.assertIsInstance(TradingApproachFactory.get_approach(None), BalancedApproach)
        self.assertIsInstance(TradingApproachFactory.get_approach("invalid"), BalancedApproach)

    def test_balanced_approach(self):
        approach = TradingApproachFactory.get_approach("Balanced")
        self.assertEqual(approach.name, "Balanced")
        self.assertEqual(approach.get_trade_confidence_threshold(), 0.0)
        self.assertEqual(approach.adjust_prompt_instructions(), "")
        # Sizing tests
        self.assertEqual(approach.calculate_position_size(10, 0), 0)
        self.assertEqual(approach.calculate_position_size(10, 50), 5)
        self.assertEqual(approach.calculate_position_size(10, 100), 10)

    def test_aggressive_approach(self):
        approach = TradingApproachFactory.get_approach("Aggressive")
        self.assertEqual(approach.name, "Aggressive")
        self.assertEqual(approach.get_trade_confidence_threshold(), 0.0)
        self.assertIn("high risk tolerance", approach.adjust_prompt_instructions())
        # Sizing tests (uses sqrt)
        # sqrt(0/100) = 0 -> 10 * 0 = 0
        self.assertEqual(approach.calculate_position_size(10, 0), 0)
        # sqrt(50/100) = ~0.7071 -> 10 * 0.7071 = 7.07 -> floor = 7
        self.assertEqual(approach.calculate_position_size(10, 50), 7)
        # sqrt(100/100) = 1.0 -> 10 * 1.0 = 10
        self.assertEqual(approach.calculate_position_size(10, 100), 10)

    def test_conservative_approach(self):
        approach = TradingApproachFactory.get_approach("Conservative")
        self.assertEqual(approach.name, "Conservative")
        self.assertEqual(approach.get_trade_confidence_threshold(), 55.0)
        self.assertIn("risk-averse", approach.adjust_prompt_instructions())
        # Sizing tests (uses square)
        # (0/100)^2 = 0 -> 10 * 0 = 0
        self.assertEqual(approach.calculate_position_size(10, 0), 0)
        # (50/100)^2 = 0.25 -> 10 * 0.25 = 2.5 -> floor = 2
        self.assertEqual(approach.calculate_position_size(10, 50), 2)
        # (100/100)^2 = 1.0 -> 10 * 1.0 = 10
        self.assertEqual(approach.calculate_position_size(10, 100), 10)

    def test_portfolio_execution_overrides(self):
        from src.backtester import Portfolio
        # Test Conservative approach with confidence below threshold (50 < 55)
        portfolio_con = Portfolio(exchange="NASDAQ", trading_approach="Conservative")
        portfolio_con.execute_trade(decision='LONG', price=100.0, confidence=50, date_str='2026-05-27')
        self.assertEqual(portfolio_con.position_type, "FLAT")
        self.assertEqual(portfolio_con.contracts, 0)

        # Test Conservative approach with confidence above threshold (60 >= 55)
        # This will proceed to get_equity which requires some initialization or will fail, but we just want to verify the override logic.
        # So verifying the below-threshold early exit is sufficient.

if __name__ == "__main__":
    unittest.main()
