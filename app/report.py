from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from uuid import uuid4
from app.data_processing import generate_report

# In-memory store to track report generation status
report_status = {}

def trigger_report_background(report_id: str, db: Session):
    """
    Runs the report generation in the background.
    """
    try:
        report_status[report_id] = "Running"
        generate_report(report_id, db)
        report_status[report_id] = "Complete"
    except Exception as e:
        report_status[report_id] = f"Failed: {str(e)}"

def trigger_report(db: Session, background_tasks: BackgroundTasks):
    """
    API-callable trigger function that queues the report job and returns report_id.
    """
    report_id = str(uuid4())  # Generate unique ID
    report_status[report_id] = "Queued"
    background_tasks.add_task(trigger_report_background, report_id, db)
    return {"report_id": report_id}

def get_report_status(report_id: str):
    """
    Returns the status of the report generation.
    """
    return report_status.get(report_id, "Not Found")
