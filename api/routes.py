from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional
from src.orchestrator import PulseOrchestrator
import pandas as pd
import io
import json
import os

router = APIRouter()
orchestrator = PulseOrchestrator()

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "Pulse Report Pipeline"}

@router.post("/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks, force: bool = False):
    """Triggers the full scrape-to-report pipeline in the background."""
    # Note: In a production app, we'd use a real task queue like Celery.
    # For this implementation, we'll use FastAPI BackgroundTasks.
    background_tasks.add_task(orchestrator.run_pipeline, force=force)
    return {"message": "Pipeline triggered successfully in the background.", "force": force}

@router.post("/upload")
async def upload_reviews(file: UploadFile = File(...)):
    """Receives a CSV/JSON of reviews for manual processing (Placeholder)."""
    if not file.filename.endswith(('.csv', '.json')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and JSON allowed.")
    
    # Logic for manual processing could go here
    return {"filename": file.filename, "status": "received", "detail": "Manual upload processing not yet implemented."}

@router.get("/reports")
async def list_reports():
    """Lists all generated pulse reports in data/processed."""
    reports = []
    processed_dir = "data/processed"
    if os.path.exists(processed_dir):
        reports = [f for f in os.listdir(processed_dir) if f.endswith('.md') or f.endswith('.html')]
    return {"reports": reports}
