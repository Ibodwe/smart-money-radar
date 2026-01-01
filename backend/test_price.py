from pykrx import stock
from datetime import datetime, timedelta

date = "20251230" # A likely valid trading day (Tuesday)

print(f"Testing price fetch for {date}")

try:
    print("--- Attempt 1: stock.get_market_ohlcv(date) ---")
    df1 = stock.get_market_ohlcv(date)
    print(df1.head())
    print(f"Shape: {df1.shape}")
except Exception as e:
    print(f"Attempt 1 failed: {e}")

try:
    print("\n--- Attempt 2: stock.get_market_ohlcv(date, market='ALL') ---")
    df2 = stock.get_market_ohlcv(date, market="ALL") # Maybe this is for filtering market
    print(df2.head())
    print(f"Shape: {df2.shape}")
except Exception as e:
    print(f"Attempt 2 failed: {e}")

try:
    print("\n--- Attempt 3: stock.get_market_ohlcv(date, date, 'ALL') (Current Code) ---")
    df3 = stock.get_market_ohlcv(date, date, "ALL")
    print(df3.head())
    print(f"Shape: {df3.shape}")
except Exception as e:
    print(f"Attempt 3 failed: {e}")
