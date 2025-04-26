# routes.py

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import uuid4
import os
import csv
import time
from sqlalchemy.sql import text

from app.database import get_db
from app.models import ReportTracker, ReportStatusEnum
from app.report import generate_report_for_store

router = APIRouter()

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# Background function to generate and save the report
def generate_and_save_report(report_id: str, db: Session):
    print(f"[DEBUG] Starting report generation for {report_id}")

    tracker = db.query(ReportTracker).filter(ReportTracker.report_id == report_id).first()
    if not tracker:
        print("[DEBUG] Tracker not found!")
        return

    try:
        store_ids = db.execute("SELECT DISTINCT store_id FROM store_status").fetchall()
        store_ids = [row[0] for row in store_ids]
        print(f"[DEBUG] Found {len(store_ids)} stores to process.")

        report_data = []
        for idx, store_id in enumerate(store_ids):
            print(f"[DEBUG] Generating report for store {store_id} ({idx+1}/{len(store_ids)})")
            try:
                report = generate_report_for_store(store_id, db)
                report_data.append([
                    store_id,
                    report.uptime_last_hour,
                    report.downtime_last_hour,
                    report.uptime_last_day,
                    report.downtime_last_day,
                    report.uptime_last_week,
                    report.downtime_last_week,
                ])
            except Exception as e:
                print(f"[ERROR] Failed for store_id={store_id}: {e}")

        print("[DEBUG] Writing report to CSV")
        filename = f"{report_id}.csv"
        file_path = os.path.join(REPORTS_DIR, filename)
        with open(file_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "store_id", "uptime_last_hour", "downtime_last_hour",
                "uptime_last_day", "downtime_last_day",
                "uptime_last_week", "downtime_last_week"
            ])
            writer.writerows(report_data)

        print(f"[DEBUG] Report file saved at {file_path}")

        tracker.status = ReportStatusEnum.complete
        tracker.file_path = file_path
        db.commit()
        print(f"[DEBUG] Tracker status updated to Complete")

    except Exception as e:
        print("[FATAL ERROR] During report generation:", e)
        db.rollback()


@router.get("/")
def root():
    return {"message": "Store Monitoring System is running!"}


@router.post("/trigger_report")
def trigger_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    report_id = str(uuid4())

    tracker = ReportTracker(
        report_id=report_id,
        status=ReportStatusEnum.running
    )
    db.add(tracker)
    db.commit()

    background_tasks.add_task(generate_and_save_report, report_id, db)

    return {"report_id": report_id}


@router.get("/get_report")
def get_report(report_id: str, db: Session = Depends(get_db)):
    tracker = db.query(ReportTracker).filter(ReportTracker.report_id == report_id).first()
    if not tracker:
        return {"error": "Invalid report_id"}

    return {
        "report_id": tracker.report_id,
        "status": tracker.status.value,
        "file_path": tracker.file_path if tracker.status == ReportStatusEnum.complete else None
    }


@router.get("/download/{report_id}")
def download_report(report_id: str, db: Session = Depends(get_db)):
    """
    Endpoint to download the report CSV if it has been generated.
    """
    tracker = db.query(ReportTracker).filter(ReportTracker.report_id == report_id).first()
    
    if not tracker:
        raise HTTPException(status_code=404, detail="Report ID not found")

    if tracker.status != ReportStatusEnum.complete:
        raise HTTPException(status_code=400, detail="Report not ready yet")

    file_path = tracker.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type='text/csv')


@router.post("/trigger_and_download_report")
def trigger_and_download(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Trigger report
    report_id = str(uuid4())

    tracker = ReportTracker(
        report_id=report_id,
        status=ReportStatusEnum.running
    )
    db.add(tracker)
    db.commit()

    background_tasks.add_task(generate_and_save_report, report_id, db)

    # 2. Polling until report is complete
    timeout_seconds = 30  # Max time to wait
    polling_interval = 2  # How often to check (in seconds)

    waited = 0
    while waited < timeout_seconds:
        db.refresh(tracker)  # Refresh tracker from database
        if tracker.status == ReportStatusEnum.complete:
            break
        time.sleep(polling_interval)
        waited += polling_interval

    if tracker.status != ReportStatusEnum.complete:
        raise HTTPException(status_code=408, detail="Report generation timed out. Try again later.")

    # 3. Download and return CSV
    file_path = tracker.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found after generation.")

    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type='text/csv')