import uvicorn
from fastapi import FastAPI
from api.routes import router
from apscheduler.schedulers.background import BackgroundScheduler
from src.orchestrator import PulseOrchestrator
from src.db_init import ensure_initialized
from utils.logger import setup_logger
from datetime import datetime

logger = setup_logger("api_server")
app = FastAPI(title="GROWW Pulse Report API", version="1.0.0")

# Include routes
app.include_router(router, prefix="/api/v1")

# Initialize Scheduler
scheduler = BackgroundScheduler()
orchestrator = PulseOrchestrator()

def scheduled_pulse_job():
    """Weekly job to trigger the pulse report."""
    logger.info("Executing scheduled weekly pulse report job...")
    result = orchestrator.run_pipeline(force=False)
    logger.info(f"Scheduled job result: {result.get('status')}")

# Add job: Every Monday at 09:00 AM
scheduler.add_job(scheduled_pulse_job, 'cron', day_of_week='mon', hour=9, minute=0)

@app.on_event("startup")
async def startup_event():
    ensure_initialized()   # schema-first, before any business logic
    logger.info("Starting Pulse Report API server...")
    scheduler.start()
    logger.info("Scheduler started successfully (Cron: Every Monday at 09:00 AM)")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Pulse Report API server...")
    scheduler.shutdown()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
