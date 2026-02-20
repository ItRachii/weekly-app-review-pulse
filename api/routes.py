from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from src.orchestrator import PulseOrchestrator
from src.email_service import EmailService
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import uuid
import os

router = APIRouter()
orchestrator = PulseOrchestrator()
_executor = ThreadPoolExecutor(max_workers=4)


class TriggerRequest(BaseModel):
    start_date: Optional[str] = None  # ISO format: "2026-02-09"
    end_date: Optional[str] = None    # ISO format: "2026-02-16"
    force: bool = False


class SendEmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = None
    report_file: str  # filename from data/processed, e.g. "pulse_email_2025-W07.html"


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "Pulse Report Pipeline"}


@router.post("/trigger")
async def trigger_pipeline(payload: TriggerRequest):
    """Accepts the trigger, schedules pipeline in a background thread, returns run_id immediately."""
    run_id = f"run_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    kwargs: dict = {"force": payload.force, "run_id": run_id}
    if payload.start_date:
        kwargs["start_date"] = datetime.fromisoformat(payload.start_date)
    if payload.end_date:
        kwargs["end_date"] = datetime.fromisoformat(payload.end_date)

    # Fire-and-forget: submit to thread pool, return immediately
    _executor.submit(orchestrator.run_pipeline, **kwargs)

    return {"status": "triggered", "run_id": run_id}


@router.post("/upload")
async def upload_reviews(file: UploadFile = File(...)):
    """Receives a CSV/JSON of reviews for manual processing (Placeholder)."""
    if not file.filename.endswith(('.csv', '.json')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and JSON allowed.")

    return {"filename": file.filename, "status": "received", "detail": "Manual upload processing not yet implemented."}


@router.get("/runs")
async def list_runs(limit: int = 20):
    """Returns all pipeline runs (any status), newest first. Used by the dashboard."""
    runs = orchestrator.data_manager.list_run_history(limit=limit)
    return {"runs": runs, "count": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Returns the current state of a single pipeline run."""
    row = orchestrator.data_manager.get_run_log(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


def _format_date_range(run: dict) -> str:
    """Helper: human-readable date range from a run_history row."""
    run_id = run.get("run_id", "")
    try:
        if run_id.startswith("custom_"):
            parts = run_id.split("_")
            if len(parts) >= 3:
                from datetime import datetime as _dt
                s = _dt.strptime(parts[1], "%Y%m%d")
                e = _dt.strptime(parts[2], "%Y%m%d")
                return f"{s.strftime('%b %d')} – {e.strftime('%b %d %Y')}"
        elif "-W" in run_id:
            from datetime import datetime as _dt
            year, week = run_id.split("-W")
            ws = _dt.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
            return f"{ws.strftime('%b %d')} – {(ws + __import__('datetime').timedelta(days=6)).strftime('%b %d %Y')}"
        elif run.get("start_date") and run.get("end_date"):
            from datetime import datetime as _dt
            s = _dt.fromisoformat(run["start_date"])
            e = _dt.fromisoformat(run["end_date"])
            return f"{s.strftime('%b %d')} – {e.strftime('%b %d %Y')}"
    except Exception:
        pass
    return "—"


@router.get("/pipeline/jobs")
async def list_pipeline_jobs(limit: int = 20):
    """
    Lightweight polling endpoint for the dashboard history table.
    Returns a stable job list with draft_report_url once the report is ready.
    Fast: single indexed DB read, no filesystem scan.
    """
    runs = orchestrator.data_manager.list_run_history(limit=limit)
    jobs = []
    for r in runs:
        run_id = r.get("run_id", "")
        email_path = os.path.join("data", "processed", f"pulse_email_{run_id}.html")
        jobs.append({
            "job_id":           run_id,
            "status":           r.get("status", "unknown"),
            "date_range":       _format_date_range(r),
            "triggered_at":     r.get("triggered_at"),
            "completed_at":     r.get("completed_at"),
            "draft_report_url": f"/?run_id={run_id}" if os.path.exists(email_path) else None,
        })
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/reports")
async def list_reports():
    """Lists all generated pulse reports with metadata (filename, type, modified date)."""
    reports = []
    processed_dir = "data/processed"
    if os.path.exists(processed_dir):
        for f in os.listdir(processed_dir):
            if f.endswith('.md') or f.endswith('.html'):
                fpath = os.path.join(processed_dir, f)
                mod_time = os.path.getmtime(fpath)
                size_bytes = os.path.getsize(fpath)
                reports.append({
                    "filename": f,
                    "type": "markdown" if f.endswith('.md') else "html",
                    "modified_at": datetime.fromtimestamp(mod_time).isoformat(),
                    "size_bytes": size_bytes
                })
        # Sort newest first
        reports.sort(key=lambda r: r["modified_at"], reverse=True)
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/{filename}")
async def get_report_content(filename: str):
    """Returns the content of a specific report file."""
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    report_path = os.path.join("data/processed", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"Report '{filename}' not found.")

    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    mime = "text/html" if filename.endswith('.html') else "text/markdown"
    return PlainTextResponse(content=content, media_type=mime)


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
