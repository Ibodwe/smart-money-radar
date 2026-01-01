import pandas as pd
from pykrx import stock
from datetime import datetime
import sys

def get_investor_data(date, investor_type):
    """
    Fetches the raw net purchase dataframe for a specific investor type on a given date.
    """
    print(f"Fetching data for {investor_type} on {date}...")
    try:
        # Arguments: fromdate, todate, market, investor
        df = stock.get_market_net_purchases_of_equities_by_ticker(date, date, "ALL", investor_type)
        
        if df.empty:
            print(f"No data found for {investor_type} on {date}.")
            return pd.DataFrame()
            
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def process_investor(date, investor_type, type_code, top_n=100):
    """
    Fetches data and saves Top N Net Buy and Top N Net Sell (most negative).
    """
    df = get_investor_data(date, investor_type)
    if df.empty:
        return False

    # 1. Net Buy (순매수) - Descending
    buy_df = df.sort_values(by='순매수거래대금', ascending=False).head(top_n)
    buy_filename = f"{type_code}_net_buy_top{top_n}_{date}.csv"
    # Simplify: Name, Net Buy Amount
    buy_df[['종목명', '순매수거래대금']].to_csv(buy_filename, encoding='utf-8-sig')
    print(f"Saved {buy_filename}")
    
    # 2. Net Sell (순매도) - Ascending (most negative net buy)
    sell_df = df.sort_values(by='순매수거래대금', ascending=True).head(top_n)
    sell_filename = f"{type_code}_net_sell_top{top_n}_{date}.csv"
    # Simplify: Name, Net Buy Amount (Negative)
    sell_df[['종목명', '순매수거래대금']].to_csv(sell_filename, encoding='utf-8-sig')
    print(f"Saved {sell_filename}")
    
    return True

def main():
    # Start from today or provided date
    target_date = datetime.now()
    if len(sys.argv) > 1:
        target_date = datetime.strptime(sys.argv[1], "%Y%m%d")

    # Try up to 10 days back
    for i in range(10):
        current_date_str = target_date.strftime("%Y%m%d")
        print(f"=== Checking Date: {current_date_str} ===")

        # Check Foreigner data availability as a proxy for valid trading day
        # We try to process Foreigner first. If successful, we assume valid day.
        
        success = process_investor(current_date_str, "외국인", "foreigner")
        
        if success:
            print(f"Data found for {current_date_str}!")
            
            # Process Individual
            process_investor(current_date_str, "개인", "individual")
            
            # Process Institution
            process_investor(current_date_str, "기관합계", "institution")
            
            return # Exit after finding the latest data

        else:
            print(f"No data for {current_date_str}. Trying previous day...")
            target_date = target_date - pd.Timedelta(days=1)
    
    print("Could not find any data in the last 10 days.")

if __name__ == "__main__":
    main()
