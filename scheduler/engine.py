"""Scheduled scraping support via APScheduler."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    job_id: str
    url: str
    schedule: str  # cron expression or interval like "5m", "1h", "1d"
    mode: str = "auto"
    format: str = "json"
    extract: list[str] = field(default_factory=list)
    active: bool = True
    last_run: str | None = None
    last_status: str | None = None
    total_runs: int = 0


class ScraperScheduler:
    """Manage scheduled scrape jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs: dict[str, ScheduledJob] = {}
        self._results: list[dict[str, Any]] = []

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    def add_job(
        self,
        url: str,
        schedule: str,
        job_id: str | None = None,
        mode: str = "auto",
        fmt: str = "json",
        extract: list[str] | None = None,
    ) -> str:
        from scraper.core.engine import ScraperFactory
        from scraper.export.formats import to_json

        import uuid

        job_id = job_id or str(uuid.uuid4())[:8]

        # Parse schedule
        if schedule.endswith("m"):
            seconds = int(schedule[:-1]) * 60
            trigger = IntervalTrigger(seconds=seconds)
        elif schedule.endswith("h"):
            seconds = int(schedule[:-1]) * 3600
            trigger = IntervalTrigger(seconds=seconds)
        elif schedule.endswith("d"):
            seconds = int(schedule[:-1]) * 86400
            trigger = IntervalTrigger(seconds=seconds)
        else:
            # Treat as cron expression
            parts = schedule.split()
            trigger = CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            )

        async def _run():
            factory = ScraperFactory(headless=True)
            try:
                data = await factory.scrape(url, mode=mode)
                result = data.to_dict()

                # Filter if requested
                if extract:
                    result = {k: v for k, v in result.items() if k in extract or k in ("url", "title")}

                await factory.close()

                self.jobs[job_id].last_run = datetime.now().isoformat()
                self.jobs[job_id].last_status = "success"
                self.jobs[job_id].total_runs += 1

                self._results.append({
                    "job_id": job_id,
                    "url": url,
                    "status": "success",
                    "data": result,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                self.jobs[job_id].last_run = datetime.now().isoformat()
                self.jobs[job_id].last_status = f"failed: {e}"
                self.jobs[job_id].total_runs += 1
                logger.error(f"Scheduled job {job_id} failed: {e}")
            finally:
                await factory.close()

        self.scheduler.add_job(_run, trigger, id=job_id, replace_existing=True)
        self.jobs[job_id] = ScheduledJob(
            job_id=job_id,
            url=url,
            schedule=schedule,
            mode=mode,
            format=fmt,
            extract=extract or [],
        )
        logger.info(f"Added scheduled job {job_id}: {url} ({schedule})")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        try:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            return True
        except Exception:
            return False

    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "job_id": j.job_id,
                "url": j.url,
                "schedule": j.schedule,
                "mode": j.mode,
                "active": j.active,
                "last_run": j.last_run,
                "last_status": j.last_status,
                "total_runs": j.total_runs,
            }
            for j in self.jobs.values()
        ]

    def get_results(self, job_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if job_id:
            return [r for r in self._results if r["job_id"] == job_id][-limit:]
        return self._results[-limit:]


# Global scheduler instance
scheduler = ScraperScheduler()
