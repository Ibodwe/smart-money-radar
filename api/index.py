from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import sys
import os

# Add project root to sys.path to allow imports from api.services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.stock_service import get_top_net_buy_sell, get_aggregated_top_stocks, analyze_special_trends
import pandas as pd
import io
import zipfile
from typing import Optional, List
from datetime import datetime, timedelta

app = FastAPI()

# Allow CORS for React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/analysis/advanced")
def get_advanced_analysis(days: int, investor: str):
    """
    Get 'Consecutive Net Buy' and 'New Inflow' stocks for the date range.
    """
    investor_map = {
        "foreigner": "외국인",
        "individual": "개인",
        "institution": "기관합계"
    }

    if investor not in investor_map:
        raise HTTPException(status_code=400, detail="Invalid investor type")
        
    result = analyze_special_trends(days, investor_map[investor])
    if result is None:
        raise HTTPException(status_code=404, detail="No data found for this period")
        
    return result

@app.get("/api/analysis/trend")
def get_analysis_trend(days: int, investor: str):
    """
    Get aggregated Top 100 net buy/sell for the past N days.
    """
    investor_map = {
        "foreigner": "외국인",
        "individual": "개인",
        "institution": "기관합계"
    }

    if investor not in investor_map:
        raise HTTPException(status_code=400, detail="Invalid investor type")
    
    # Calculate date range (Trading Days)
    from api.services.stock_service import get_start_date_n_trading_days_ago
    
    end_date = datetime.now()
    end_str = end_date.strftime("%Y%m%d")
    start_str = get_start_date_n_trading_days_ago(days)
    
    result = get_aggregated_top_stocks(start_str, end_str, investor_map[investor])
    if result is None:
        raise HTTPException(status_code=404, detail="No data found for this period")
        
    return result

@app.get("/api/data")
def get_daily_data(date: str, investor: str):
    """
    Get top 100 net buy/sell for a given date and investor.
    investor: 'foreigner', 'individual', 'institution'
    """
    investor_map = {
        "foreigner": "외국인",
        "individual": "개인",
        "institution": "기관합계"
    }
    
    if investor not in investor_map:
        raise HTTPException(status_code=400, detail="Invalid investor type")

    result = get_top_net_buy_sell(date, investor_map[investor])
    if result is None:
        raise HTTPException(status_code=404, detail="No data found for this date")
    
    return result

@app.get("/api/download")
def download_data(start_date: str, end_date: str, investors: Optional[List[str]] = Query(None)):
    """
    Download ZIP containing CSVs for the date range.
    investors: list of 'foreigner', 'individual', 'institution' (default all)
    """
    investor_map = {
        "foreigner": "외국인",
        "individual": "개인",
        "institution": "기관합계"
    }
    
    target_investors = investors if investors else ["foreigner", "individual", "institution"]
    
    # Generate date range
    try:
        dates = pd.date_range(start=start_date, end=end_date).strftime("%Y%m%d").tolist()
    except:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYYMMDD)")

    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files_added = False
        for d in dates:
            for inv_code in target_investors:
                inv_name = investor_map.get(inv_code)
                if not inv_name: continue
                
                data = get_top_net_buy_sell(d, inv_name, allow_fallback=False)
                if data:
                    # Create Net Buy CSV
                    buy_df = pd.DataFrame(data['buy'])
                    if not buy_df.empty:
                        # Simplify columns: Name, Net Buy Amount
                        buy_csv = buy_df[['name', 'net_buy_amount']].to_csv(index=False, header=['Name', 'Net Buy Amount'])
                        zip_file.writestr(f"{inv_code}_net_buy_{d}.csv", buy_csv)
                        files_added = True

                    # Create Net Sell CSV
                    sell_df = pd.DataFrame(data['sell'])
                    if not sell_df.empty:
                        # Simplify columns: Name, Net Buy Amount
                        sell_csv = sell_df[['name', 'net_buy_amount']].to_csv(index=False, header=['Name', 'Net Buy Amount'])
                        zip_file.writestr(f"{inv_code}_net_sell_{d}.csv", sell_csv)
                        files_added = True
    
    if not files_added:
        raise HTTPException(status_code=404, detail="No data found for the specified range")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename=stock_data_{start_date}_{end_date}.zip"}
    )
