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
        self.assertIn("You are a disciplined, balanced trader.", approach.adjust_prompt_instructions())
        # Sizing tests
        self.assertEqual(approach.calculate_position_size(10, 0), 0)
        self.assertEqual(approach.calculate_position_size(10, 50), 5)
        self.assertEqual(approach.calculate_position_size(10, 100), 10)

    def test_aggressive_approach(self):
        approach = TradingApproachFactory.get_approach("Aggressive")
        self.assertEqual(approach.name, "Aggressive")
        self.assertEqual(approach.get_trade_confidence_threshold(), 0.0)
        self.assertIn("aggressive momentum trader", approach.adjust_prompt_instructions())
        # Sizing tests (uses 0.7 exponent)
        # 0^0.7 = 0 -> 10 * 0 = 0
        self.assertEqual(approach.calculate_position_size(10, 0), 0)
        # 0.5^0.7 = ~0.615 -> 10 * 0.615 = 6.15 -> floor = 6
        self.assertEqual(approach.calculate_position_size(10, 50), 6)
        # 1^0.7 = 1.0 -> 10 * 1.0 = 10
        self.assertEqual(approach.calculate_position_size(10, 100), 10)

    def test_conservative_approach(self):
        approach = TradingApproachFactory.get_approach("Conservative")
        self.assertEqual(approach.name, "Conservative")
        self.assertEqual(approach.get_trade_confidence_threshold(), 55.0)
        self.assertIn("conservative capital preservation specialist", approach.adjust_prompt_instructions())
        # Sizing tests (uses square)
        # (0/100)^2 = 0 -> 10 * 0 = 0
        self.assertEqual(approach.calculate_position_size(10, 0), 0)
        # (50/100)^2 = 0.25 -> 10 * 0.25 = 2.5 -> floor = 2
        self.assertEqual(approach.calculate_position_size(10, 50), 2)
        # (100/100)^2 = 1.0 -> 10 * 1.0 = 10
        self.assertEqual(approach.calculate_position_size(10, 100), 10)

    def test_portfolio_execution_overrides(self):
        from src.backtester import Portfolio
        
        # Test 1: Conservative approach with confidence below threshold (54 < 55) -> overridden to HOLD
        portfolio_con_54 = Portfolio(exchange="NASDAQ", initial_cash=100000.0, trading_approach="Conservative")
        portfolio_con_54.execute_trade(decision='LONG', price=100.0, confidence=54, date_str='2026-05-27')
        self.assertEqual(portfolio_con_54.position_type, "FLAT")
        self.assertEqual(portfolio_con_54.contracts, 0)

        # Test 2: Conservative approach with confidence exactly at threshold (55 >= 55) -> executes LONG
        portfolio_con_55 = Portfolio(exchange="NASDAQ", initial_cash=100000.0, trading_approach="Conservative")
        portfolio_con_55.execute_trade(decision='LONG', price=100.0, confidence=55, date_str='2026-05-27')
        self.assertEqual(portfolio_con_55.position_type, "LONG")
        self.assertEqual(portfolio_con_55.contracts, 1)
        self.assertEqual(portfolio_con_55.entry_price, 100.0)

    def test_parse_llm_response(self):
        from src.llm_agent import parse_llm_response
        
        # Test 1: Simple valid JSON
        r1 = '{"decision": "LONG", "confidence": 75, "reasoning": "Standard response."}'
        res1 = parse_llm_response(r1)
        self.assertEqual(res1["decision"], "LONG")
        self.assertEqual(res1["confidence"], 75)
        self.assertEqual(res1["reasoning"], "Standard response.")

        # Test 2: Double JSON blocks (rfind issue)
        r2 = '{"decision": "SHORT", "confidence": 60, "reasoning": "First block."} {"meta": "extra"}'
        res2 = parse_llm_response(r2)
        self.assertEqual(res2["decision"], "SHORT")
        self.assertEqual(res2["confidence"], 60)
        self.assertEqual(res2["reasoning"], "First block.")

        # Test 3: Nested braces within reasoning string
        r3 = '{"decision": "LONG", "confidence": 80, "reasoning": "Indices like {NASDAQ} are bullish."}'
        res3 = parse_llm_response(r3)
        self.assertEqual(res3["decision"], "LONG")
        self.assertEqual(res3["confidence"], 80)
        self.assertEqual(res3["reasoning"], "Indices like {NASDAQ} are bullish.")

        # Test 4: Escaped quotes inside JSON string containing braces
        r4 = '{"decision": "FLAT", "confidence": 50, "reasoning": "He said \\"this is {normal}\\" today."}'
        res4 = parse_llm_response(r4)
        self.assertEqual(res4["decision"], "FLAT")
        self.assertEqual(res4["confidence"], 50)
        self.assertEqual(res4["reasoning"], 'He said "this is {normal}" today.')

        # Test 5: Fallback to rfind if no matching closing brace is found
        r5 = '{"decision": "LONG", "confidence": 90, "reasoning": "No matching close'
        res5 = parse_llm_response(r5)
        self.assertEqual(res5["decision"], "HOLD") # JSON loads fails, returns default HOLD

if __name__ == "__main__":
    unittest.main()
