"""
Scheduler - Runs the pipeline daily at a configured time
"""

import asyncio
import argparse
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from main import ReasoningVideoPipeline
from src.utils.logger import setup_logger, get_logger


def run_daily_pipeline():
    """Run the daily video generation pipeline."""
    setup_logger(log_file="logs/scheduler.log")
    logger = get_logger("Scheduler")

    logger.info(f"=== Daily pipeline started at {datetime.now()} ===")

    try:
        pipeline = ReasoningVideoPipeline()
        result = asyncio.run(pipeline.run())

        if result["success"]:
            logger.info(f"Daily pipeline SUCCESS - Part {result['part']}")
            if result.get("youtube_url"):
                logger.info(f"Video URL: {result['youtube_url']}")
        else:
            logger.error(f"Daily pipeline FAILED: {result.get('error')}")

    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="Reasoning Video Scheduler")
    parser.add_argument("--time", type=str, default="10:00",
                        help="Time to run daily (HH:MM format, default: 10:00)")
    parser.add_argument("--timezone", type=str, default="Asia/Kolkata",
                        help="Timezone (default: Asia/Kolkata)")
    parser.add_argument("--run-now", action="store_true",
                        help="Run once immediately")

    args = parser.parse_args()

    setup_logger(log_file="logs/scheduler.log")
    logger = get_logger("Scheduler")

    if args.run_now:
        logger.info("Running pipeline immediately...")
        run_daily_pipeline()
        return

    hour, minute = args.time.split(":")

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=int(hour), minute=int(minute), timezone=args.timezone),
        id="daily_reasoning_video",
        name="Daily Reasoning Video Generation",
        misfire_grace_time=3600
    )

    logger.info(f"Scheduler started - will run daily at {args.time} ({args.timezone})")
    print(f"Scheduler running. Daily video at {args.time} {args.timezone}. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
