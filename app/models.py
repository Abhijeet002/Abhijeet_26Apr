from app.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Time


# Creating tables
class BusinessHour(Base):
    __tablename__= "menu_hours"
    id = Column(Integer, primary_key =True, index=True)
    store_id = Column(Integer, index= True)
    day =Column(Integer)
    start_time_local = Column(Time)
    end = Column(Time)

    

class StoreStatus(Base):
    __tablename__= "store_status"
    id = Column(Integer, primary_key= True, index= True)
    store_id = Column(Integer, index= True)
    timestamp_utc = Column(DateTime)
    status = Column(String)


class StoreTimeZone(Base):
    __tablename__ = "store_timezones"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, unique=True, index=True)
    timezone_str = Column(String)  



