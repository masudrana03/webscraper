"""FastAPI REST API for the web scraper."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from scraper.core.engine import ScraperFactory
from scraper.export.formats import to_csv, to_html, to_json, to_markdown
from scheduler.engine import scheduler as task_scheduler
from api.ui import mount_ui
from api.logging_config import setup_logging, get_logger

# ---------- Logging ----------
LOG_FILE = setup_logging()
log = get_logger("api")

log.info("=" * 60)
log.info("WebScraper API starting up")
log.info("Log file: %s", LOG_FILE)
log.info("=" * 60)

app = FastAPI(
    title="WebScraper API",
    description="Paste any URL, scrape everything. Aggressive multi-strategy scraper.",
    version="1.0.0",
)

# ---------- API Router (all endpoints under /api) ----------
from fastapi import APIRouter

api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory job store (swap with Redis/DB for production)
jobs: dict[str, dict[str, Any]] = {}

# Scraper factory (singleton)
scraper: ScraperFactory | None = None


@app.on_event("startup")
async def startup():
    global scraper
    log.info("Initializing scraper engine (headless=True, timeout=30)")
    scraper = ScraperFactory(headless=True, timeout=30)
    task_scheduler.start()
    log.info("Startup complete - ready to serve requests")


@app.on_event("shutdown")
async def shutdown():
    log.info("Shutting down...")
    if scraper:
        await scraper.close()
        log.info("Scraper engine closed")
    task_scheduler.stop()
    log.info("Shutdown complete")


# ---------- Request / Response Models ----------

class ScrapeRequest(BaseModel):
    url: str
    mode: str = "auto"  # auto, static, headless
    format: str = "json"  # json, csv, markdown, html
    proxy: str | None = None
    extra_wait: int = 2  # seconds to wait for JS rendering
    scroll: bool = True  # scroll to load lazy content
    extract: list[str] | None = None  # filter what to extract: links, images, emails, phones, tables, text, social


class ScrapeResponse(BaseModel):
    job_id: str
    url: str
    status: str
    created_at: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    file: str | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None


# ---------- Endpoints ----------

@api.get("/")
async def root():
    log.debug("API root accessed")
    return {
        "service": "WebScraper API",
        "version": "1.0.0",
        "endpoints": {
            "POST /scrape": "Scrape a URL",
            "POST /scrape/sync": "Scrape a URL (blocking)",
            "GET /scrape/{job_id}": "Get job status/result",
            "GET /jobs": "List all jobs",
            "DELETE /jobs": "Clear all jobs",
            "GET /health": "Health check",
        },
    }


@api.get("/health")
async def health():
    log.debug("Health check")
    return {"status": "ok"}


@api.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "url": req.url,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "result": None,
        "file": None,
        "error": None,
    }
    background_tasks.add_task(_run_scrape, job_id, req)
    log.info("ASYNC SCRAPE | job=%s | url=%s | mode=%s | format=%s", job_id, req.url, req.mode, req.format)
    return ScrapeResponse(job_id=job_id, url=req.url, status="pending", created_at=jobs[job_id]["created_at"])


@api.post("/scrape/sync")
async def scrape_sync(req: ScrapeRequest):
    """Blocking scrape - returns result directly. Use for quick scrapes."""
    log.info("SYNC SCRAPE START | url=%s | mode=%s | format=%s | extract=%s", req.url, req.mode, req.format, req.extract)
    t0 = time.time()
    try:
        result = await _do_scrape(req)
        elapsed = round(time.time() - t0, 2)

        if req.format == "html":
            content = to_html(result)
            log.info("SYNC SCRAPE DONE | url=%s | format=html | elapsed=%ss | size=%d chars", req.url, elapsed, len(content))
            return {"format": "html", "content": content}
        elif req.format == "markdown":
            content = to_markdown(result)
            log.info("SYNC SCRAPE DONE | url=%s | format=markdown | elapsed=%ss | size=%d chars", req.url, elapsed, len(content))
            return {"format": "markdown", "content": content}
        elif req.format == "csv":
            content = to_csv(result)
            log.info("SYNC SCRAPE DONE | url=%s | format=csv | elapsed=%ss | size=%d chars", req.url, elapsed, len(content))
            return {"format": "csv", "content": content}

        log.info("SYNC SCRAPE DONE | url=%s | format=json | elapsed=%ss", req.url, elapsed)
        return {"format": "json", **result}
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        log.error("SYNC SCRAPE FAIL | url=%s | error=%s | elapsed=%ss", req.url, str(e), elapsed)
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/scrape/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    log.debug("GET JOB | job=%s", job_id)
    if job_id not in jobs:
        log.warning("JOB NOT FOUND | job=%s", job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@api.get("/jobs")
async def list_jobs(limit: int = Query(default=50, le=200)):
    log.debug("LIST JOBS | total=%d | limit=%d", len(jobs), limit)
    return list(jobs.values())[-limit:]


@api.delete("/jobs")
async def clear_jobs():
    count = len(jobs)
    jobs.clear()
    log.info("CLEARED JOBS | removed=%d", count)
    return {"cleared": count}


# ---------- Scheduled Scraping ----------

class ScheduleRequest(BaseModel):
    url: str
    schedule: str  # cron: "0 */6 * * *" or interval: "30m", "2h", "1d"
    mode: str = "auto"
    format: str = "json"
    extract: list[str] | None = None


@api.post("/schedule")
async def create_schedule(req: ScheduleRequest):
    log.info("SCHEDULE CREATE | url=%s | schedule=%s | mode=%s | format=%s", req.url, req.schedule, req.mode, req.format)
    job_id = task_scheduler.add_job(
        url=req.url,
        schedule=req.schedule,
        mode=req.mode,
        fmt=req.format,
        extract=req.extract,
    )
    return {"job_id": job_id, "url": req.url, "schedule": req.schedule, "status": "active"}


@api.get("/schedule")
async def list_schedules():
    log.debug("LIST SCHEDULES")
    return task_scheduler.list_jobs()


@api.delete("/schedule/{job_id}")
async def remove_schedule(job_id: str):
    log.info("SCHEDULE REMOVE | job=%s", job_id)
    if task_scheduler.remove_job(job_id):
        return {"status": "removed", "job_id": job_id}
    log.warning("SCHEDULE NOT FOUND | job=%s", job_id)
    raise HTTPException(status_code=404, detail="Schedule not found")


@api.get("/schedule/{job_id}/results")
async def get_schedule_results(job_id: str, limit: int = Query(default=20, le=100)):
    log.debug("SCHEDULE RESULTS | job=%s | limit=%d", job_id, limit)
    return task_scheduler.get_results(job_id, limit)


# ---------- Background Worker ----------

async def _run_scrape(job_id: str, req: ScrapeRequest):
    jobs[job_id]["status"] = "processing"
    log.info("BG SCRAPE START | job=%s | url=%s | mode=%s | format=%s", job_id, req.url, req.mode, req.format)
    t0 = time.time()
    try:
        result = await _do_scrape(req)

        # Filter extracted data if requested
        if req.extract:
            filtered = {"url": result["url"], "title": result["title"]}
            for key in req.extract:
                if key in result:
                    filtered[key] = result[key]
            result = filtered

        # Save to file
        fmt = req.format or "json"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{job_id}_{timestamp}"
        filepath = OUTPUT_DIR / f"{filename}.{fmt}"

        if fmt == "html":
            to_html(result, str(filepath))
        elif fmt == "markdown":
            to_markdown(result, str(filepath))
        elif fmt == "csv":
            to_csv(result, str(filepath))
        else:
            to_json(result, str(filepath))

        elapsed = round(time.time() - t0, 2)
        log.info("BG SCRAPE DONE | job=%s | format=%s | file=%s | elapsed=%ss", job_id, fmt, filepath, elapsed)

        jobs[job_id].update({
            "status": "completed",
            "result": result,
            "file": str(filepath),
            "completed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        log.error("BG SCRAPE FAIL | job=%s | error=%s | elapsed=%ss", job_id, str(e), elapsed)
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })


async def _do_scrape(req: ScrapeRequest) -> dict[str, Any]:
    """Execute the scrape using the factory."""
    if not scraper:
        raise RuntimeError("Scraper not initialized")

    log.debug("SCRAPING | url=%s | mode=%s | extra_wait=%s", req.url, req.mode, req.extra_wait)
    result = await scraper.scrape(
        url=req.url,
        mode=req.mode,
        extra_wait=req.extra_wait,
    )
    data = result.to_dict()
    log.debug("SCRAPED | url=%s | title=%s | links=%d | images=%d | emails=%d",
              req.url, data.get("title", ""), len(data.get("links", [])),
              len(data.get("images", [])), len(data.get("emails", [])))
    return data


# ---------- Mount API Router + Web UI (UI must be last) ----------
app.include_router(api)
mount_ui(app)
