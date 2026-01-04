from sqlalchemy import Column, String, BigInteger, Integer, Float
from api.database import Base

class StockData(Base):
    __tablename__ = "stock_data"

    # Composite primary key: date + investor + ticker
    date = Column(String, primary_key=True, index=True) # YYYYMMDD
    investor = Column(String, primary_key=True, index=True) # foreigner, individual, institution
    ticker = Column(String, primary_key=True, index=True)
    
    name = Column(String)
    net_buy_amount = Column(BigInteger) # 순매수거래대금

class MarketPrice(Base):
    __tablename__ = "market_price"
    
    date = Column(String, primary_key=True, index=True)
    ticker = Column(String, primary_key=True, index=True)
    
    close_price = Column(Integer)
    fluctuation_rate = Column(Float)
