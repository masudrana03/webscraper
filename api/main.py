"""FastAPI REST API for the web scraper."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from scraper.core.engine import ScraperFactory
from scraper.export.formats import to_csv, to_html, to_json, to_markdown
from scheduler.engine import scheduler as task_scheduler
from api.ui import mount_ui

app = FastAPI(
    title="WebScraper API",
    description="Paste any URL, scrape everything. Aggressive multi-strategy scraper.",
    version="1.0.0",
)

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
    scraper = ScraperFactory(headless=True, timeout=30)
    task_scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    if scraper:
        await scraper.close()
    task_scheduler.stop()


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

@app.get("/")
async def root():
    return {
        "service": "WebScraper API",
        "version": "1.0.0",
        "endpoints": {
            "POST /scrape": "Scrape a URL",
            "GET /scrape/{job_id}": "Get job status/result",
            "GET /jobs": "List all jobs",
            "DELETE /jobs": "Clear all jobs",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
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
    return ScrapeResponse(job_id=job_id, url=req.url, status="pending", created_at=jobs[job_id]["created_at"])


@app.post("/scrape/sync")
async def scrape_sync(req: ScrapeRequest):
    """Blocking scrape - returns result directly. Use for quick scrapes."""
    try:
        result = await _do_scrape(req)
        if req.format == "html":
            return {"format": "html", "content": to_html(result)}
        elif req.format == "markdown":
            return {"format": "markdown", "content": to_markdown(result)}
        elif req.format == "csv":
            return {"format": "csv", "content": to_csv(result)}
        return {"format": "json", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scrape/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/jobs")
async def list_jobs(limit: int = Query(default=50, le=200)):
    return list(jobs.values())[-limit:]


@app.delete("/jobs")
async def clear_jobs():
    count = len(jobs)
    jobs.clear()
    return {"cleared": count}


# ---------- Scheduled Scraping ----------

class ScheduleRequest(BaseModel):
    url: str
    schedule: str  # cron: "0 */6 * * *" or interval: "30m", "2h", "1d"
    mode: str = "auto"
    format: str = "json"
    extract: list[str] | None = None


@app.post("/schedule")
async def create_schedule(req: ScheduleRequest):
    job_id = task_scheduler.add_job(
        url=req.url,
        schedule=req.schedule,
        mode=req.mode,
        fmt=req.format,
        extract=req.extract,
    )
    return {"job_id": job_id, "url": req.url, "schedule": req.schedule, "status": "active"}


@app.get("/schedule")
async def list_schedules():
    return task_scheduler.list_jobs()


@app.delete("/schedule/{job_id}")
async def remove_schedule(job_id: str):
    if task_scheduler.remove_job(job_id):
        return {"status": "removed", "job_id": job_id}
    raise HTTPException(status_code=404, detail="Schedule not found")


@app.get("/schedule/{job_id}/results")
async def get_schedule_results(job_id: str, limit: int = Query(default=20, le=100)):
    return task_scheduler.get_results(job_id, limit)


# ---------- Background Worker ----------

async def _run_scrape(job_id: str, req: ScrapeRequest):
    jobs[job_id]["status"] = "processing"
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

        jobs[job_id].update({
            "status": "completed",
            "result": result,
            "file": str(filepath),
            "completed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })


async def _do_scrape(req: ScrapeRequest) -> dict[str, Any]:
    """Execute the scrape using the factory."""
    if not scraper:
        raise RuntimeError("Scraper not initialized")

    result = await scraper.scrape(
        url=req.url,
        mode=req.mode,
        extra_wait=req.extra_wait,
    )
    return result.to_dict()


# ---------- Mount Web UI (must be last) ----------
mount_ui(app)
