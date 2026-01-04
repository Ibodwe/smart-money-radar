from pykrx import stock
import pandas as pd
from datetime import datetime

def test_pykrx():
    date = "20240105"
    ticker = "005930" # Samsung Electronics
    
    print(f"Testing basic OHLCV for {ticker} on {date}...")
    try:
        df = stock.get_market_ohlcv(date, date, ticker)
        print("Result:")
        print(df)
        if df.empty:
            print("Empty DataFrame returned.")
        else:
            print("Success!")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting Net Purchases for {date} (Foreigner)...")
    try:
        # Try KOSPI
        print("Trying KOSPI...")
        df = stock.get_market_net_purchases_of_equities_by_ticker(date, date, "KOSPI", "외국인")
        print(f"KOSPI Result Empty? {df.empty}")
        if not df.empty:
            print(df.head())
            
        # Try KOSDAQ
        print("Trying KOSDAQ...")
        df2 = stock.get_market_net_purchases_of_equities_by_ticker(date, date, "KOSDAQ", "외국인")
        print(f"KOSDAQ Result Empty? {df2.empty}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pykrx()
