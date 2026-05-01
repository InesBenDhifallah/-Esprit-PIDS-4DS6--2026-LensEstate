"""
Scheduler — runs the pipeline every 6 hours automatically.
Start with: python scheduler.py
Keep this running in a terminal or as a Windows service.
"""

import schedule
import time
import logging
from pipeline import run_pipeline

log = logging.getLogger('scheduler')

def job():
    log.info("Scheduler triggered pipeline run")
    try:
        run_pipeline()
    except Exception as e:
        log.error(f"Scheduled run failed: {e}")

# run every 6 hours
schedule.every(6).hours.do(job)

# also run immediately on startup
schedule.every().day.at("02:00").do(job)  # daily at 2 AM

log.info("Scheduler started. Pipeline will run every 6 hours.")
log.info("Press Ctrl+C to stop.")

# run once immediately on start
job()

while True:
    schedule.run_pending()
    time.sleep(60)