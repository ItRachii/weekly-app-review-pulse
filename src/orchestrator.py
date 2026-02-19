import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.scraper_engine import ScraperEngine
from src.theme_engine import ThemeClusteringEngine
from src.report_generator import PulseReportGenerator
from src.email_generator import EmailGenerator
from src.data_manager import DataManager
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
        self.data_manager = DataManager()
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
        # 0. Handle Date Defaults
        current_end = end_date or datetime.now()
        current_start = start_date or (current_end - timedelta(weeks=self.weeks_back))

        # If dates are provided, we skip the standard week-based idempotency check
        # and treat it as a custom run.
        is_custom_run = start_date is not None or end_date is not None
        
        if is_custom_run:
            # Format: custom_START_END_TIMESTAMP
            timestamp = datetime.now().strftime('%H%M%S')
            start_str = current_start.strftime('%Y%m%d')
            end_str = current_end.strftime('%Y%m%d')
            run_id = f"custom_{start_str}_{end_str}_{timestamp}"
        else:
            run_id = self._get_week_id()

        if not force and not is_custom_run and self._already_run_this_week():
            msg = f"Pipeline already run for {run_id}. Use force=True to override."
            logger.info(msg)
            return {"status": "skipped", "reason": msg}

        try:
            # 1. Incremental Scrape & Clean

            # 1. Incremental Scrape & Clean
            logger.info(f"Stage 1/4: Intelligent Scraping ({current_start.date()} to {current_end.date()})...")
            
            platforms = [
                {"name": "ios", "id": "1404871703"},
                {"name": "android", "id": "com.groww"}
            ]
            
            for platform in platforms:
                missing_ranges = self.db.get_missing_ranges(current_start, current_end, platform["name"])
                
                # Check if this is the first time for this platform
                if len(missing_ranges) == 1 and missing_ranges[0] == (current_start, current_end):
                    has_history = self.db.has_platform_history(platform["name"])
                    if not has_history:
                        logger.info(f"Initial run detected for {platform['name']}. Performing full sync for the requested range.")
                
                if not missing_ranges:
                    logger.info(f"Cache Hit: All data for {platform['name']} is already available.")
                    continue
                
                for m_start, m_end in missing_ranges:
                    logger.info(f"Scraping {platform['name']} for missing range: {m_start.date()} to {m_end.date()}")
                    scraper = ScraperEngine(start_date=m_start, end_date=m_end)
                    
                    if platform["name"] == "ios":
                        new_reviews = scraper.scrape_app_store(app_id=platform["id"])
                    else:
                        # Increased count to 500 for better date range coverage on popular apps
                        new_reviews = scraper.scrape_play_store(package_name=platform["id"], count=500)
                    
                    if new_reviews:
                        saved = self.db.save_reviews(new_reviews)
                        logger.info(f"Saved {saved}/{len(new_reviews)} new reviews for {platform['name']}")
                    else:
                        logger.info(f"No new reviews found for {platform['name']} in this sub-range.")
                    
                    # Mark as scraped regardless of finding reviews, so we don't infinitely retry empty days.
                    # But we trust DataManager.save_reviews wouldn't crash.
                    self.db.mark_scraped(platform["name"], m_start, m_end)

            # 2. Fetch all reviews (Cached + Just Scraped) for the requested range
            all_reviews = self.db.get_cached_reviews(current_start, current_end)
            
            if not all_reviews:
                raise PulsePipelineError("No reviews found in the requested date range.", "Scraping")

            logger.info(f"Total reviews for analysis: {len(all_reviews)}")
            reviews_path = f"data/raw/reviews_{run_id}.json"
            with open(reviews_path, 'w', encoding='utf-8') as f:
                json.dump(all_reviews, f, indent=2, default=str)

            # 3. Cluster
            logger.info("Stage 2/4: Clustering Themes...")
            engine = ThemeClusteringEngine()
            themes_objs = engine.cluster_reviews(all_reviews)
            themes = [t.model_dump() if hasattr(t, 'model_dump') else t.dict() for t in themes_objs]

            analysis_path = f"data/processed/analysis_{run_id}.json"
            with open(analysis_path, 'w', encoding='utf-8') as f:
                json.dump(themes, f, indent=2)

            # 4. Generate Reports
            logger.info("Stage 3/4: Generating Reports...")
            report_gen = PulseReportGenerator()
            pulse_note = report_gen.generate_note(themes)
            
            # Calculate stats for Email Snapshot
            total_reviews = len(all_reviews)
            avg_rating = sum(r['rating'] for r in all_reviews) / total_reviews if total_reviews > 0 else 0
            critical_issues_count = sum(1 for r in all_reviews if r['rating'] <= 2)
            
            stats = {
                "total_reviews": total_reviews,
                "avg_rating": avg_rating,
                "critical_issues_count": critical_issues_count
            }

            email_html = EmailGenerator.generate_html(themes, stats)

            note_path = f"data/processed/pulse_note_{run_id}.md"
            email_path = f"data/processed/pulse_email_{run_id}.html"
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(pulse_note)
            with open(email_path, 'w', encoding='utf-8') as f:
                f.write(email_html)

            # Persist run log
            self.data_manager.save_run_log({
                "run_id": run_id,
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "reviews_processed": total_reviews,
                "themes_identified": len(themes)
            })

            # 5. Finalize
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
            logger.info(f"Pipeline completed successfully for {run_id}")
            return result

        except Exception as e:
            stage = getattr(e, 'stage', 'Unknown')
            error_msg = f"Pipeline failed at stage [{stage}]: {str(e)}"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg, "stage": stage}

    def purge_all_data(self):
        """
        Completely purges all reviews, reports, logs, and database records.
        """
        logger.warning("Initiating full data purge...")
        
        # 1. Clear Files
        dirs_to_clean = ['data/raw', 'data/processed']
        for d in dirs_to_clean:
            if os.path.exists(d):
                for f in os.listdir(d):
                    file_path = os.path.join(d, f)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")

        # 2. Reset Database
        self.db.reset_database()

        # 3. Truncate Logs
        log_path = 'logs/pulse_pipeline.log'
        if os.path.exists(log_path):
            try:
                # Open in write mode and immediately close to truncate
                with open(log_path, 'w'):
                    pass
            except Exception as e:
                logger.error(f"Failed to truncate logs: {e}")
                
        logger.info("Full data purge completed successfully.")
        return True


