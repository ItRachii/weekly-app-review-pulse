from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from typing import Optional
from src.orchestrator import PulseOrchestrator
from src.email_service import EmailService
from datetime import datetime
import os

router = APIRouter()
orchestrator = PulseOrchestrator()


class SendEmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = None
    report_file: str  # filename from data/processed, e.g. "pulse_email_2025-W07.html"


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "Pulse Report Pipeline"}

@router.post("/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks, force: bool = False):
    """Triggers the full scrape-to-report pipeline in the background."""
    background_tasks.add_task(orchestrator.run_pipeline, force=force)
    return {"message": "Pipeline triggered successfully in the background.", "force": force}

@router.post("/upload")
async def upload_reviews(file: UploadFile = File(...)):
    """Receives a CSV/JSON of reviews for manual processing (Placeholder)."""
    if not file.filename.endswith(('.csv', '.json')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and JSON allowed.")
    
    return {"filename": file.filename, "status": "received", "detail": "Manual upload processing not yet implemented."}

@router.get("/reports")
async def list_reports():
    """Lists all generated pulse reports in data/processed."""
    reports = []
    processed_dir = "data/processed"
    if os.path.exists(processed_dir):
        reports = [f for f in os.listdir(processed_dir) if f.endswith('.md') or f.endswith('.html')]
    return {"reports": reports}

@router.delete("/purge")
async def purge_all_data(x_confirm: str = Header(alias="X-Confirm-Purge")):
    """
    Purges ALL reviews, reports, logs, and database records.
    Requires the header `X-Confirm-Purge: delete` as a safety guard.
    """
    if x_confirm.lower() != "delete":
        raise HTTPException(
            status_code=400,
            detail="Safety check failed. Send header 'X-Confirm-Purge: delete' to confirm."
        )
    
    success = orchestrator.purge_all_data()
    if success:
        return {"status": "purged", "message": "All data has been purged successfully."}
    raise HTTPException(status_code=500, detail="Purge operation failed. Check server logs.")

@router.post("/send-email")
async def send_email_report(payload: SendEmailRequest):
    """Sends a generated HTML report via email."""
    report_path = os.path.join("data/processed", payload.report_file)
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"Report file '{payload.report_file}' not found.")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    subject = payload.subject or f"[GROWW] Weekly App Review Pulse - {datetime.now().strftime('%B %d, %Y')}"
    
    success = EmailService.send_email(
        to_email=payload.to_email,
        subject=subject,
        html_content=html_content
    )
    
    if success:
        return {"status": "sent", "to": payload.to_email, "report": payload.report_file}
    raise HTTPException(status_code=500, detail="Failed to send email. Check SMTP configuration in .env.")
