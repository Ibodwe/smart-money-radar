from datetime import datetime, timedelta
from api.services import stock_service

def update_daily_data():
    """
    Job to be run daily at midnight.
    Fetches data for the previous day (latest completed trading day) to ensure DB is populated.
    """
    print("Running daily stock data update job...")
    
    # At midnight (00:00), we want the data for the day that just ended (yesterday).
    target_date = datetime.now() - timedelta(days=1)
    date_str = target_date.strftime("%Y%m%d")
    
    investors = ["외국인", "개인", "기관합계"]
    
    for investor in investors:
        print(f"Updating data for {date_str}, {investor}...")
        try:
            # tailored function to force update?
            # get_top_net_buy_sell will check DB first. 
            # If we want to FORCE update, we might need to verify if DB has it. 
            # But if it's a new day, DB won't have it, so it will fetch from pykrx.
            # So just calling this is enough.
            stock_service.get_top_net_buy_sell(date_str, investor)
        except Exception as e:
            print(f"Error updating {date_str} {investor}: {e}")
            
    print("Daily stock data update job completed.")
