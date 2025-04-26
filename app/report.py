# from fastapi import BackgroundTasks
# from sqlalchemy.orm import Session
# from uuid import uuid4
# from app.data_processing import generate_report
# from app.models import StoreStatus  # or wherever your store status model is


# # In-memory store to track report generation status
# report_status = {}

class Report:
    def __init__(self, uptime_last_hour, downtime_last_hour, uptime_last_day, downtime_last_day, uptime_last_week, downtime_last_week):
        self.uptime_last_hour = uptime_last_hour
        self.downtime_last_hour = downtime_last_hour
        self.uptime_last_day = uptime_last_day
        self.downtime_last_day = downtime_last_day
        self.uptime_last_week = uptime_last_week
        self.downtime_last_week = downtime_last_week

# def generate_report_for_store(store_id: int, db: Session) -> Report:
#     # Your logic to compute uptime/downtime across hour/day/week
#     # Dummy values for now
#     return Report(50, 10, 300, 60, 1800, 120)


# def trigger_report_background(report_id: str, db: Session):
#     """
#     Runs the report generation in the background.
#     """
#     try:
#         report_status[report_id] = "Running"
#         generate_report(report_id, db)
#         report_status[report_id] = "Complete"
#     except Exception as e:
#         report_status[report_id] = f"Failed: {str(e)}"

# def trigger_report(db: Session, background_tasks: BackgroundTasks):
#     """
#     API-callable trigger function that queues the report job and returns report_id.
#     """
#     report_id = str(uuid4())  # Generate unique ID
#     report_status[report_id] = "Queued"
#     background_tasks.add_task(trigger_report_background, report_id, db)
#     return {"report_id": report_id}

# def get_report_status(report_id: str):
#     """
#     Returns the status of the report generation.
#     """
#     return report_status.get(report_id, "Not Found")



# report.py
from datetime import datetime, timedelta
import pytz
from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.models import StoreTimeZone, BusinessHour, StoreStatus  # Import the StoreTimeZone, BusinessHour, and StoreStatus models

def generate_report_for_store(store_id: int, db: Session) -> Report:
    now_utc = datetime.utcnow()
    

    # Get the timezone for the store
    store_timezone_entry = db.query(StoreTimeZone).filter(StoreTimeZone.store_id == str(store_id)).first()
    if store_timezone_entry:
        store_tz = pytz.timezone(store_timezone_entry.timezone_str)
    else:
        store_tz = pytz.utc  # Default to UTC if timezone not found

    now_local = now_utc.astimezone(store_tz)

    # Get business hours for this store
    business_hours = db.query(BusinessHour).filter(BusinessHour.store_id == store_id).all()
    business_hours_by_day = {bh.day: (bh.start_time_local, bh.end_time_local) for bh in business_hours}

    # Time ranges
    ranges = {
        'last_hour': now_utc - timedelta(hours=1),
        'last_day': now_utc - timedelta(days=1),
        'last_week': now_utc - timedelta(weeks=1),
    }

    results = {}

    for key, start_time in ranges.items():
        uptime_minutes = 0
        downtime_minutes = 0

        # Query statuses between start_time and now
        statuses = db.query(StoreStatus).filter(
            StoreStatus.store_id == store_id,
            StoreStatus.timestamp_utc >= start_time,
            StoreStatus.timestamp_utc <= now_utc
        ).order_by(StoreStatus.timestamp_utc).all()

        # If no statuses, assume full downtime
        if not statuses:
            results[key] = (0, int((now_utc - start_time).total_seconds() // 60))
            continue

        last_status = None
        last_time = start_time

        for status_entry in statuses:
            status_time_local = status_entry.timestamp_utc.astimezone(store_tz)
            weekday = status_time_local.weekday()

            # Check if within business hours
            if weekday in business_hours_by_day:
                start_local, end_local = business_hours_by_day[weekday]
                if start_local <= status_time_local.time() <= end_local:
                    minutes = int((status_entry.timestamp_utc - last_time).total_seconds() // 60)

                    if last_status == "active":
                        uptime_minutes += minutes
                    elif last_status == "inactive":
                        downtime_minutes += minutes
                    else:
                        # If we don't know, assume downtime
                        downtime_minutes += minutes

                    last_time = status_entry.timestamp_utc
                    last_status = status_entry.status

        # After last status to now
        final_minutes = int((now_utc - last_time).total_seconds() // 60)
        if last_status == "active":
            uptime_minutes += final_minutes
        elif last_status == "inactive":
            downtime_minutes += final_minutes
        else:
            downtime_minutes += final_minutes

        results[key] = (uptime_minutes, downtime_minutes)

    return Report(
        uptime_last_hour=results['last_hour'][0],
        downtime_last_hour=results['last_hour'][1],
        uptime_last_day=results['last_day'][0],
        downtime_last_day=results['last_day'][1],
        uptime_last_week=results['last_week'][0],
        downtime_last_week=results['last_week'][1],
    )
