import logging
import argparse
from src.orchestrator import PulseOrchestrator
from utils.logger import setup_logger

logger = setup_logger("cli")

def main():
    parser = argparse.ArgumentParser(description="Weekly App Review Pulse CLI")
    parser.add_argument("--weeks", type=int, default=12, help="Number of weeks to look back")
    parser.add_argument("--force", action="store_true", help="Force run ignoring idempotency")
    args = parser.parse_args()

    logger.info(f"Starting Pulse CLI (Lookback: {args.weeks} weeks)")
    
    orchestrator = PulseOrchestrator(weeks_back=args.weeks)
    result = orchestrator.run_pipeline(force=args.force)

    if result["status"] == "success":
        print("\n" + "="*50)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("="*50)
        print(f"Week ID: {result['week_id']}")
        print(f"Reviews Processed: {result['reviews_count']}")
        print(f"Analysis: {result['artifacts']['analysis']}")
        print(f"Executive Note: {result['artifacts']['pulse_note']}")
    else:
        print(f"\nPipeline {result['status']}: {result.get('reason') or result.get('error')}")

if __name__ == "__main__":
    main()
