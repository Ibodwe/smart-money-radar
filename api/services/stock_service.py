import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta

import os

# Database cache handling
from api.database import SessionLocal
from api.models import StockData
from sqlalchemy.orm import Session

def get_investor_data(date, investor_type):
    """
    Fetches the raw net purchase dataframe for a specific investor type on a given date.
    Checks Local DB -> fetch from pykrx -> save to DB
    Args:
        date (str): YYYYMMDD format
        investor_type (str): '외국인', '개인', '기관합계'
    """
    db: Session = SessionLocal()
    try:
        # 1. Check DB first
        cached_data = db.query(StockData).filter(
            StockData.date == date, 
            StockData.investor == investor_type
        ).all()
        
        if cached_data:
            print(f"Using cached data from DB for {date} {investor_type} ({len(cached_data)} records)")
            # Convert to DataFrame
            data = [{
                '티커': item.ticker,
                '종목명': item.name,
                '순매수거래대금': item.net_buy_amount
            } for item in cached_data]
            
            df = pd.DataFrame(data)
            df.set_index('티커', inplace=True)
            return df
            
        # 2. Fetch from pykrx if not in DB
        print(f"Fetching from pykrx for {date} {investor_type}...")
        try:
             # get_market_net_purchases_of_equities_by_ticker(fromdate, todate, market, investor)
            df = stock.get_market_net_purchases_of_equities_by_ticker(date, date, "ALL", investor_type)
            if not df.empty:
                # Save to DB
                print(f"Saving {len(df)} records to DB...")
                new_records = []
                for ticker, row in df.iterrows():
                    # Check if relevant (maybe only save if non-zero? No, save all to be complete cache)
                    # But for performance and storage, maybe Top N? User wants "pykrx data" to be cached.
                    # Pykrx returns ALL tickers. That's approx 2500 rows.
                    # SQLite can handle it easily.
                    
                    obj = StockData(
                        date=date,
                        investor=investor_type,
                        ticker=str(ticker),
                        name=row['종목명'],
                        net_buy_amount=int(row['순매수거래대금'])
                    )
                    new_records.append(obj)
                
                # Bulk insert
                db.bulk_save_objects(new_records)
                db.commit()
                
                return df
                
        except Exception as e:
            print(f"Error fetching data from pykrx: {e}")

    finally:
        db.close()

    # 3. Fallback: Try loading from local CSVs
    print(f"Attempting fallback to local CSV for {date}, {investor_type}")
    
    investor_code_map = {
        "외국인": "foreigner",
        "개인": "individual",
        "기관합계": "institution"
    }
    
    inv_code = investor_code_map.get(investor_type)
    if not inv_code:
        return pd.DataFrame()
        
    # We look for files in the project root (parent of api/services/../../)
    # Just assume current working dir is project root or check relative paths
    # The app is running from project root usually.
    
    buy_file = f"{inv_code}_net_buy_top100_{date}.csv"
    sell_file = f"{inv_code}_net_sell_top100_{date}.csv"
    
    combined_df = pd.DataFrame()
    
    if os.path.exists(buy_file):
        try:
            buy_df = pd.read_csv(buy_file)
            # CSV columns: 티커, 종목명, 순매수거래대금
            # We want Ticker as index
            if '티커' in buy_df.columns:
                # Ensure ticker is string (e.g. 005930, not 5930)
                buy_df['티커'] = buy_df['티커'].astype(str).str.zfill(6)
                buy_df.set_index('티커', inplace=True)
                combined_df = pd.concat([combined_df, buy_df])
        except Exception as e:
            print(f"Error reading buy csv {buy_file}: {e}")

    if os.path.exists(sell_file):
        try:
            sell_df = pd.read_csv(sell_file)
            if '티커' in sell_df.columns:
                sell_df['티커'] = sell_df['티커'].astype(str).str.zfill(6)
                sell_df.set_index('티커', inplace=True)
                combined_df = pd.concat([combined_df, sell_df])
        except Exception as e:
             print(f"Error reading sell csv {sell_file}: {e}")
             
    if not combined_df.empty:
        # Remove duplicates if any (though buy/sell sets should be disjoint ideally)
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
        print(f"Loaded {len(combined_df)} records from CSV for {date}")
        return combined_df

    return pd.DataFrame()

def get_start_date_n_trading_days_ago(days):
    """
    Finds the date that is 'days' trading days ago from today (inclusive).
    Uses KOSPI index or similar to identify business days.
    """
    end_date = datetime.now()
    # Fetch a large enough range of calendar days to ensure we cover enough trading days
    # 2.5 * days + buffer
    lookback = days * 3 + 20
    start_lookback = end_date - timedelta(days=lookback)
    
    start_str = start_lookback.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    try:
        # Fetch KOSPI index to get valid business days
        # "1001" is KOSPI
        df = stock.get_index_ohlcv_by_date(start_str, end_str, "1001")
        if df.empty:
            # Fallback to calendar days if API fails
            print("Warning: Failed to fetch business days, falling back to calendar days.")
            return (end_date - timedelta(days=days)).strftime("%Y%m%d")
            
        # df.index are the business days
        business_days = df.index.sort_values(ascending=False).tolist()
        
        # We want to include today? No, 'past N days' usually means [today-N+1 ... today] or similar.
        # If user says 1 day, it means today (or last trading day).
        # If user says 2 days, it means today + yesterday (trading).
        
        if len(business_days) < days:
             # Not enough data found, return the earliest we have
             return business_days[-1].strftime("%Y%m%d")
             
        # business_days[0] is the latest available trading day.
        # Nth day is index days-1
        target_day = business_days[days-1]
        return target_day.strftime("%Y%m%d")
        
    except Exception as e:
        print(f"Error determining business days: {e}")
        return (end_date - timedelta(days=days)).strftime("%Y%m%d")

def get_market_price(date):
    """
    Fetches OHLCV data to get Close price and Fluctuation rate.
    Returns DataFrame with columns ['종가', '등락률']
    """
    try:
        # Correct usage: (date, market="ALL")
        df = stock.get_market_ohlcv(date, market="ALL")
        if df.empty:
            return pd.DataFrame()
        return df[['종가', '등락률']]
    except Exception as e:
        print(f"Error fetching price data: {e}")
        return pd.DataFrame()


def get_nearest_market_price(date_str):
    """
    Tries to get market price for date_str.
    If empty (holiday), looks back up to 5 days to find the nearest trading day.
    """
    target = pd.to_datetime(date_str, format="%Y%m%d")
    
    for _ in range(7): # 1 week lookback
        curr_str = target.strftime("%Y%m%d")
        df = get_market_price(curr_str)
        if not df.empty:
            return df
        target -= timedelta(days=1)
    
    return pd.DataFrame()

def get_top_net_buy_sell(date, investor_type, top_n=100, allow_fallback=True):
    """
    Returns a dictionary with 'buy' and 'sell' lists.
    Each list contains dicts with 'name', 'net_buy_amount'.
    """
    MAX_DAYS_BACK = 10 if allow_fallback else 0
    
    # Try current date and go back up to MAX_DAYS_BACK
    target_date = pd.to_datetime(date, format='%Y%m%d')
    
    for _ in range(MAX_DAYS_BACK + 1):
        current_date_str = target_date.strftime("%Y%m%d")
        df = get_investor_data(current_date_str, investor_type)
        
        if not df.empty:
            # Fetch price data for the same date
            price_df = get_market_price(current_date_str)
            
            # Helper to safely get price info
            def get_price_info(ticker):
                if not price_df.empty and ticker in price_df.index:
                    return int(price_df.loc[ticker]['종가']), round(float(price_df.loc[ticker]['등락률']), 2)
                return 0, 0.0

            # 1. Net Buy (Descending)
            buy_df = df.sort_values(by='순매수거래대금', ascending=False).head(top_n)
            buy_data = []
            for ticker, row in buy_df.iterrows():
                price, chg = get_price_info(ticker)
                buy_data.append({
                    "ticker": ticker,
                    "name": row['종목명'],
                    "net_buy_amount": int(row['순매수거래대금']),
                    "close_price": price,
                    "percent_change": chg,
                    "rank": len(buy_data) + 1
                })

            # 2. Net Sell (Ascending - most negative)
            sell_df = df.sort_values(by='순매수거래대금', ascending=True).head(top_n)
            sell_data = []
            for ticker, row in sell_df.iterrows():
                price, chg = get_price_info(ticker)
                sell_data.append({
                    "ticker": ticker,
                    "name": row['종목명'],
                    "net_buy_amount": int(row['순매수거래대금']),
                    "close_price": price,
                    "percent_change": chg,
                    "rank": len(sell_data) + 1
                })
            
            return {
                "buy": buy_data,
                "sell": sell_data,
                "date": current_date_str
            }
        
        # Go back 1 day
        target_date -= pd.Timedelta(days=1)
    
    return None

def get_aggregated_investor_data(start_date, end_date, investor_type):
    """
    Fetches the aggregated net purchase dataframe for a specific investor type over a date range.
    """
    try:
        # get_market_net_purchases_of_equities_by_ticker returns aggregated sum for the period
        df = stock.get_market_net_purchases_of_equities_by_ticker(start_date, end_date, "ALL", investor_type)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"Error fetching aggregated data: {e}")
        return pd.DataFrame()

def get_aggregated_top_stocks(start_date, end_date, investor_type, top_n=100):
    """
    Returns aggregated Top N Net Buy/Sell over a period.
    """
    df = get_aggregated_investor_data(start_date, end_date, investor_type)
    if df.empty:
        return None

    # Fetch price data for the end_date (latest status)
    # Fetch price data for the end_date (latest status)
    price_df = get_nearest_market_price(end_date)
    
    def get_price_info(ticker):
        if not price_df.empty and ticker in price_df.index:
             return int(price_df.loc[ticker]['종가']), round(float(price_df.loc[ticker]['등락률']), 2)
        return 0, 0.0

    # 1. Net Buy (Descending)
    buy_df = df.sort_values(by='순매수거래대금', ascending=False).head(top_n)
    buy_data = []
    for ticker, row in buy_df.iterrows():
        price, chg = get_price_info(ticker)
        buy_data.append({
            "ticker": ticker,
            "name": row['종목명'],
            "net_buy_amount": int(row['순매수거래대금']),
            "close_price": price,
            "percent_change": chg,
            "rank": len(buy_data) + 1
        })

    # 2. Net Sell (Ascending - most negative)
    sell_df = df.sort_values(by='순매수거래대금', ascending=True).head(top_n)
    sell_data = []
    for ticker, row in sell_df.iterrows():
        price, chg = get_price_info(ticker)
        sell_data.append({
            "ticker": ticker,
            "name": row['종목명'],
            "net_buy_amount": int(row['순매수거래대금']),
            "close_price": price,
            "percent_change": chg,
            "rank": len(sell_data) + 1
        })
    
    return {
        "buy": buy_data,
        "sell": sell_data,
        "start_date": start_date,
        "end_date": end_date
    }

from concurrent.futures import ThreadPoolExecutor, as_completed

def get_daily_raw_data(date, investor_type):
    """Helper to fetch raw dataframe for a single day"""
    try:
        df = stock.get_market_net_purchases_of_equities_by_ticker(date, date, "ALL", investor_type)
        return date, df
    except:
        return date, pd.DataFrame()

def analyze_special_trends(days, investor_type, top_n=20):
    """
    Analyzes:
    1. Consecutive Net Buy for N days
    2. First Net Buy (New Inflow) after N-1 days of selling/neutral
    """
    # 1. Get valid business days
    end_date = datetime.now()
    # We need to find 'days' number of valid trading days. 
    # Since we can't easily predict holidays, we look back (days * 2) and take the last 'days' valid ones.
    # For simplicity, we just check the last 'days' calendar days first, 
    # but a better approach is to check data availability.
    
    # Efficient approach: Try to fetch last N+5 business days using pykrx's date tool if available, 
    # or just iterate back until we collect 'days' valid datasets.
    
    valid_datasets = [] # list of (date, df) sorted desc (today first)
    
    # We'll fetch a bit more to ensure we get enough valid days
    # Try to find 'days' * 2 to account for weekends/holidays
    search_limit = days * 2 + 5
    target_date = end_date
    dates_to_check = []
    
    while len(dates_to_check) < search_limit:
        date_str = target_date.strftime("%Y%m%d")
        dates_to_check.append(date_str)
        target_date -= timedelta(days=1)
    
    # Parallel fetch
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_daily_raw_data, d, investor_type) for d in dates_to_check]
        
        raw_results = []
        for future in as_completed(futures):
            d, df = future.result()
            if not df.empty:
                raw_results.append((d, df))
    
    # Sort by date descending (Newest first)
    raw_results.sort(key=lambda x: x[0], reverse=True)
    
    # We strictly need valid data.
    if not raw_results:
        return None

    # Filter to ensure we have at least 'days' of data if possible, 
    # but strictly we should use what we found if we want "consecutive over available days".
    # User asked for "N days", so ideally we want N valid trading days.
    if len(raw_results) > days:
        raw_results = raw_results[:days]
    
    today_date, today_df = raw_results[0]
    oldest_date, _ = raw_results[-1]
    
    # Fetch price data for today_date (latest) and oldest_date (start)
    price_df = get_nearest_market_price(today_date)
    start_price_df = get_nearest_market_price(oldest_date)
    
    # 1. Consecutive Net Buy
    # Start with today's buyers
    consecutive_buyers = set(today_df[today_df['순매수거래대금'] > 0].index)
    
    for _, df in raw_results[1:]:
        day_buyers = set(df[df['순매수거래대금'] > 0].index)
        consecutive_buyers = consecutive_buyers.intersection(day_buyers)
        
    # 2. New Inflow (First Net Buy)
    # Today > 0, and ALL previous days <= 0 (or not present, if not present assumed 0 or neutral)
    new_inflow = set(today_df[today_df['순매수거래대금'] > 0].index)
    
    for _, df in raw_results[1:]:
        # If bought on any previous day, remove from new_inflow
        day_buyers = set(df[df['순매수거래대금'] > 0].index)
        new_inflow = new_inflow - day_buyers

    def build_result_list(tickers):
        res = []
        for ticker in tickers:
            # Get details from today_df
            if ticker in today_df.index:
                row = today_df.loc[ticker]
                end_price = 0
                end_chg = 0.0 # fallback daily
                start_price = 0

                if not price_df.empty and ticker in price_df.index:
                    end_price = int(price_df.loc[ticker]['종가'])
                    end_chg = round(float(price_df.loc[ticker]['등락률']), 2)

                if not start_price_df.empty and ticker in start_price_df.index:
                    start_price = int(start_price_df.loc[ticker]['종가'])

                final_chg = end_chg
                if start_price > 0 and end_price > 0:
                    period_change = (end_price - start_price) / start_price * 100
                    final_chg = round(period_change, 2)

                res.append({
                    "ticker": ticker,
                    "name": row['종목명'],
                    "net_buy_amount": int(row['순매수거래대금']),
                    "close_price": end_price,
                    "percent_change": final_chg,
                    "rank": 0 # rank will be assigned after sort
                })
        # Sort by amount desc
        res.sort(key=lambda x: x['net_buy_amount'], reverse=True)
        # Assign rank
        for i, item in enumerate(res):
            item['rank'] = i + 1
        return res[:top_n]

    today_date, _ = raw_results[0]
    oldest_date, _ = raw_results[-1]
    
    return {
        "consecutive": build_result_list(consecutive_buyers),
        "new_inflow": build_result_list(new_inflow),
        "days_analyzed": len(raw_results),
        "start_date": oldest_date,
        "end_date": today_date
    }

def get_price_changes(start_date, end_date, tickers):
    """
    Fetches price change data for the given period.
    Returns a dict: {ticker: fluctuation_rate}
    """
    try:
        # get_market_price_change_by_ticker calculates change from start to end
        df = stock.get_market_price_change_by_ticker(start_date, end_date)
        if df.empty:
            return {}
        # '등락률' is the column percentage
        return df['등락률'].to_dict()
    except Exception as e:
        print(f"Error fetching price changes: {e}")
        return {}

def enrich_with_price_change(data_list, price_map):
    """Helper to add fluctuation_rate to the list objects"""
    for item in data_list:
        ticker = item['ticker']
        if ticker in price_map:
            item['percent_change'] = round(price_map[ticker], 2)
        else:
            item['percent_change'] = 0.0
    return data_list

# Update existing functions to use this (Monkey-patching logic flow or re-implementing needed parts)
# Since I can't easily jump around, I'll redefine get_aggregated_top_stocks and analyze_special_trends completely 
# if I were rewriting the file, but here I will just REDEFINE the ones I need or splice them in.
# Actually, I need to modify get_aggregated_top_stocks and analyze_special_trends.

