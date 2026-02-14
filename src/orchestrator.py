import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.scraper_engine import ScraperEngine
from src.theme_engine import ThemeClusteringEngine
from src.report_generator import PulseReportGenerator
from src.email_generator import EmailGenerator
from utils.logger import setup_logger

logger = setup_logger("orchestrator")

class PulsePipelineError(Exception):
    """Custom exception for pipeline failures."""
    def __init__(self, message: str, stage: str):
        super().__init__(message)
        self.stage = stage

class PulseOrchestrator:
    """
    Orchestrates the Weekly Pulse pipeline: 
    Scrape -> Clean -> Cluster -> Report -> Email.
    Includes idempotency and structured error handling.
    """
    
    MANIFEST_FILE = "data/processed/run_manifest.json"

    def __init__(self, weeks_back: int = 12):
        self.weeks_back = weeks_back
        os.makedirs('data/raw', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)

    def _get_week_id(self) -> str:
        """Returns a YYYY-WW identifier for the current week."""
        return datetime.now().strftime("%Y-W%W")

    def _already_run_this_week(self) -> bool:
        """Checks the manifest if a run has already completed for this week."""
        if not os.path.exists(self.MANIFEST_FILE):
            return False
            
        try:
            with open(self.MANIFEST_FILE, 'r') as f:
                manifest = json.load(f)
                return self._get_week_id() in manifest.get("completed_weeks", [])
        except Exception as e:
            logger.error(f"Failed to read manifest: {e}")
            return False

    def _mark_week_completed(self):
        """Adds the current week to the completed manifest."""
        week_id = self._get_week_id()
        manifest = {"completed_weeks": []}
        
        if os.path.exists(self.MANIFEST_FILE):
            try:
                with open(self.MANIFEST_FILE, 'r') as f:
                    manifest = json.load(f)
            except:
                pass
        
        if week_id not in manifest["completed_weeks"]:
            manifest["completed_weeks"].append(week_id)
            with open(self.MANIFEST_FILE, 'w') as f:
                json.dump(manifest, f, indent=2)

    def run_pipeline(self, force: bool = False, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Executes the full pipeline.
        :param force: If True, bypasses idempotency check.
        :param start_date: Optional start date for scraping.
        :param end_date: Optional end date for scraping.
        """
        # If dates are provided, we skip the standard week-based idempotency check
        # and treat it as a custom run.
        is_custom_run = start_date is not None or end_date is not None
        run_id = self._get_week_id() if not is_custom_run else f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not force and not is_custom_run and self._already_run_this_week():
            msg = f"Pipeline already run for {run_id}. Use force=True to override."
            logger.info(msg)
            return {"status": "skipped", "reason": msg}

        try:
            # 1. Scrape & Clean
            logger.info("Stage 1/4: Scraping and Cleansing...")
            scraper = ScraperEngine(start_date=start_date, end_date=end_date, weeks_back=self.weeks_back)
            ios_reviews = scraper.scrape_app_store(app_id="1404871703")
            android_reviews = scraper.scrape_play_store(package_name="com.groww", count=150)
            all_reviews = ios_reviews + android_reviews
            
            if not all_reviews:
                raise PulsePipelineError("No reviews found during scraping.", "Scraping")

            reviews_path = f"data/raw/reviews_{run_id}.json"
            with open(reviews_path, 'w', encoding='utf-8') as f:
                json.dump(all_reviews, f, indent=2, default=str)

            # 2. Cluster
            logger.info("Stage 2/4: Clustering Themes...")
            engine = ThemeClusteringEngine()
            themes_objs = engine.cluster_reviews(all_reviews)
            themes = [t.model_dump() if hasattr(t, 'model_dump') else t.dict() for t in themes_objs]

            analysis_path = f"data/processed/analysis_{run_id}.json"
            with open(analysis_path, 'w', encoding='utf-8') as f:
                json.dump(themes, f, indent=2)

            # 3. Generate Reports
            logger.info("Stage 3/4: Generating Reports...")
            report_gen = PulseReportGenerator()
            pulse_note = report_gen.generate_note(themes)
            
            email_html = EmailGenerator.generate_html(themes)

            note_path = f"data/processed/pulse_note_{run_id}.md"
            email_path = f"data/processed/pulse_email_{run_id}.html"
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(pulse_note)
            with open(email_path, 'w', encoding='utf-8') as f:
                f.write(email_html)

            if not is_custom_run:
                self._mark_week_completed()
            
            result = {
                "status": "success",
                "run_id": run_id,
                "reviews_count": len(all_reviews),
                "themes_count": len(themes),
                "artifacts": {
                    "raw_reviews": reviews_path,
                    "analysis": analysis_path,
                    "pulse_note": note_path,
                    "email_html": email_path
                }
            }
            logger.info(f"Pipeline completed successfully for {self._get_week_id()}")
            return result

        except Exception as e:
            stage = getattr(e, 'stage', 'Unknown')
            error_msg = f"Pipeline failed at stage [{stage}]: {str(e)}"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg, "stage": stage}
