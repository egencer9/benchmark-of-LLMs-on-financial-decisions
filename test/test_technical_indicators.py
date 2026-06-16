import sys
import os
import unittest
import pandas as pd
import numpy as np

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.technical_indicators import compute_rsi, compute_sma, compute_macd, compute_bollinger_pctb, compute_price_changes

class TestTechnicalIndicators(unittest.TestCase):
    def test_rsi_pure_gains(self):
        # 16 days of strictly increasing prices (gains only)
        prices = pd.Series([100.0 + i for i in range(16)])
        rsi = compute_rsi(prices)
        self.assertEqual(rsi, 100.0)

    def test_rsi_pure_losses(self):
        # 16 days of strictly decreasing prices (losses only)
        prices = pd.Series([100.0 - i for i in range(16)])
        rsi = compute_rsi(prices)
        self.assertEqual(rsi, 0.0)

    def test_rsi_flat_prices(self):
        # 16 days of unchanged prices (flat)
        prices = pd.Series([100.0] * 16)
        rsi = compute_rsi(prices)
        self.assertEqual(rsi, 50.0)

    def test_rsi_insufficient_data(self):
        # Less than period + 1 (14 + 1 = 15) days of data
        prices = pd.Series([100.0 + i for i in range(10)])
        rsi = compute_rsi(prices)
        self.assertEqual(rsi, 50.0)

    def test_rsi_normal_variation(self):
        # Normal series with gains and losses
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106, 105, 107, 106, 108, 107, 109, 108, 110, 109, 111])
        rsi = compute_rsi(prices)
        # Should be a valid float between 0 and 100
        self.assertTrue(0.0 < rsi < 100.0)
        self.assertEqual(rsi, 69.32)

    def test_sma_calculations(self):
        prices = pd.Series([10, 20, 30, 40, 50])
        # Normal SMA (period 3) -> (30 + 40 + 50) / 3 = 40.0
        sma_val = compute_sma(prices, 3)
        self.assertEqual(sma_val, 40.0)

        # SMA Fallback when data is shorter than period
        sma_fallback = compute_sma(prices, 10)
        self.assertEqual(sma_fallback, 50.0)  # Should return last element

    def test_bollinger_pctb_normal(self):
        prices = pd.Series([10.0] * 19 + [12.0])  # length 20
        pctb = compute_bollinger_pctb(prices, period=20)
        # price is 12, mean is 10.1, std is 0.447 -> upper is 10.99, lower is 9.20
        # Should be greater than 1.0 (above upper band)
        self.assertTrue(pctb > 1.0)

    def test_bollinger_pctb_flat(self):
        # If all prices are flat, std is 0. Bollinger Bands collapse.
        prices = pd.Series([10.0] * 20)
        pctb = compute_bollinger_pctb(prices, period=20)
        self.assertEqual(pctb, 0.5)

    def test_macd_insufficient_data(self):
        # MACD requires slow + signal = 26 + 9 = 35 days
        prices = pd.Series([100.0] * 20)
        macd_res = compute_macd(prices)
        self.assertEqual(macd_res, {"macd": 0.0, "signal": 0.0, "histogram": 0.0})

    def test_price_changes(self):
        prices = pd.Series([100.0, 105.0])
        changes = compute_price_changes(prices)
        # 1d change: ((105 - 100)/100) * 100 = 5.0%
        self.assertEqual(changes["1d"], 5.0)
        # 5d and 10d should be 0.0 due to insufficient data
        self.assertEqual(changes["5d"], 0.0)
        self.assertEqual(changes["10d"], 0.0)

if __name__ == "__main__":
    unittest.main()
