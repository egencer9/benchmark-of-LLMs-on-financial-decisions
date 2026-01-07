import sys
import os
sys.path.append(os.getcwd())
import src.backtester as bt
import config

# Manually override config to ensure it works
config.TRADING_MODE = 'futures'
config.FUTURES_CONFIG = {
    'ticker': 'MNQ',
    'contract_name': 'Micro E-mini Nasdaq-100',
    'margin_per_contract': 2000,
    'point_multiplier': 2.0,
    'tick_size': 0.25,
    'tick_value': 0.50
}

portfolio = bt.Portfolio(initial_cash=100000)
print(f"Initial Cash: ${portfolio.cash}")

# Step 1: BUY
print("\n--- TEST: BUY 5 Contracts @ 25,000 ---")
# Confidence 1.0, trade_fraction 0.1 => 10,000 allocation.
# Margin = 2000. 10,000 / 2000 = 5 contracts.
portfolio.execute_trade('^NDX', 'BUY', price=25000, confidence=1.0, trade_fraction=0.1)

print(f"Post-Buy Free Cash: ${portfolio.cash:,.2f}")
print(f"Holdings: {portfolio.holdings}")

assert portfolio.cash == 90000, f"Expected 90k, got {portfolio.cash}"
assert portfolio.holdings['^NDX']['quantity'] == 5, "Expected 5 contracts"

# Step 2: CHECK VALUATION
print("\n--- TEST: VALUATION @ 25,100 (+100 points) ---")
# Prices went up 100 points.
# P&L = 100 points * $2 * 5 contracts = $1,000.
# Locked Margin = 5 * 2000 = 10,000.
# Free Cash = 90,000.
# Total Equity should be 90k + 10k + 1k = 101,000.
total_val = portfolio.get_total_value({'^NDX': 25100})
print(f"Total Portfolio Value: ${total_val:,.2f}")

assert total_val == 101000, f"Expected 101000, got {total_val}"

# Step 3: SELL
print("\n--- TEST: SELL ALL @ 25,200 (+200 points from entry) ---")
# Prices went up 200 points total.
# P&L = 200 * $2 * 5 = $2,000.
# Margin returned = 10,000.
# Cash before sell = 90,000.
# New Cash = 90,000 + 10,000 + 2,000 = 102,000.
portfolio.execute_trade('^NDX', 'SELL', price=25200, confidence=1.0)

print(f"Post-Sell Free Cash: ${portfolio.cash:,.2f}")
print(f"Holdings: {portfolio.holdings}")

assert portfolio.cash == 102000, f"Expected 102,000, got {portfolio.cash}"
assert '^NDX' not in portfolio.holdings, "Holdings should be empty"

print("\nSUCCESS: Futures Logic Verified Correctly.")
