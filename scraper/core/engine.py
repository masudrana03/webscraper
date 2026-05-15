"""Core scraper engine - handles all scraping strategies."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


@dataclass
class ScrapedData:
    """Universal result container for any scrape."""

    url: str
    status_code: int = 0
    title: str = ""
    description: str = ""
    text_content: str = ""
    html: str = ""
    links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    videos: list[dict[str, str]] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    social_links: list[dict[str, str]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    stylesheets: list[str] = field(default_factory=list)
    og_tags: dict[str, str] = field(default_factory=dict)
    structured_data: list[dict[str, Any]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class StaticScraper:
    """Fast HTTP-based scraper for static pages."""

    def __init__(self, proxy: str | None = None, timeout: int = 30):
        self.proxy = proxy
        self.timeout = timeout

    async def scrape(self, url: str, **kwargs) -> ScrapedData:
        headers = kwargs.get("headers", self._default_headers())

        async with httpx.AsyncClient(
            proxy=self.proxy,
            timeout=self.timeout,
            follow_redirects=True,
            verify=False,
            headers=headers,
        ) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

            return self._parse(url, resp.text, resp.status_code, dict(resp.headers))

    def _default_headers(self) -> dict[str, str]:
        from fake_useragent import UserAgent

        ua = UserAgent()
        return {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _parse(self, url: str, html: str, status_code: int, resp_headers: dict) -> ScrapedData:
        soup = BeautifulSoup(html, "lxml")
        data = ScrapedData(url=url, status_code=status_code, html=html, headers=resp_headers)

        # Title
        data.title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Meta
        meta_desc = soup.find("meta", attrs={"name": "description"})
        data.description = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else ""

        # All metadata
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property", "")
            content = meta.get("content", "")
            if name and content:
                data.metadata[name] = content

        # Open Graph tags
        for meta in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
            prop = meta.get("property", "")
            data.og_tags[prop] = meta.get("content", "")

        # Structured data (JSON-LD)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data.structured_data.append(json.loads(script.string))
            except (json.JSONDecodeError, TypeError):
                pass

        # Text content (clean)
        for tag in soup(["script", "style", "nav", "footer", "noscript", "iframe"]):
            tag.decompose()
        data.text_content = soup.get_text(separator="\n", strip=True)

        # Links
        parsed_base = urlparse(url)
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if parsed_base.netloc in urlparse(href).netloc or urlparse(href).scheme:
                data.links.append({
                    "text": a.get_text(strip=True)[:200],
                    "href": href,
                })

        # Images
        for img in soup.find_all("img"):
            src = urljoin(url, img.get("src", "")) if img.get("src") else ""
            data.images.append({
                "src": src,
                "alt": img.get("alt", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
            })

        # Videos
        for video in soup.find_all("video"):
            src = video.get("src", "")
            if src:
                data.videos.append({"src": urljoin(url, src), "type": "video"})

        for iframe in soup.find_all("iframe"):
            src = iframe.get("src", "")
            if src and ("youtube" in src or "vimeo" in src):
                data.videos.append({"src": src, "type": "embed"})

        # Emails
        data.emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", data.text_content)))

        # Phones
        data.phones = list(set(re.findall(r"(?:\+?880|01)[3-9]\d{8}|\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}", data.text_content)))

        # Social links
        social_domains = ["facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com", "youtube.com", "github.com", "tiktok.com", "pinterest.com"]
        for link in data.links:
            for domain in social_domains:
                if domain in link["href"]:
                    data.social_links.append(link)
                    break

        # Tables
        for table in soup.find_all("table"):
            rows = []
            headers_row = []
            for th in table.find_all("th"):
                headers_row.append(th.get_text(strip=True))
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    if headers_row:
                        rows.append(dict(zip(headers_row, cells)))
                    else:
                        rows.append({"cells": cells})
            if rows:
                data.tables.append({"headers": headers_row, "rows": rows})

        # Forms
        for form in soup.find_all("form"):
            form_data = {
                "action": urljoin(url, form.get("action", "")),
                "method": form.get("method", "GET").upper(),
                "fields": [],
            }
            for inp in form.find_all(["input", "textarea", "select"]):
                field_info = {
                    "name": inp.get("name", ""),
                    "type": inp.get("type", "text"),
                    "placeholder": inp.get("placeholder", ""),
                    "required": inp.has_attr("required"),
                }
                if field_info["name"]:
                    form_data["fields"].append(field_info)
            data.forms.append(form_data)

        # Scripts & stylesheets
        for s in soup.find_all("script", src=True):
            data.scripts.append(urljoin(url, s["src"]))
        for link in soup.find_all("link", rel="stylesheet", href=True):
            data.stylesheets.append(urljoin(url, link["href"]))

        return data


class HeadlessScraper:
    """Playwright-based scraper for JS-rendered pages (React, Vue, SPA)."""

    def __init__(self, proxy: str | None = None, headless: bool = True, timeout: int = 30):
        self.proxy = proxy
        self.headless = headless
        self.timeout = timeout
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def startup(self):
        self._playwright = await async_playwright().start()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        browser_args = {
            "headless": self.headless,
            "args": launch_args,
        }
        if self.proxy:
            browser_args["proxy"] = {"server": self.proxy}

        self._browser = await self._playwright.chromium.launch(**browser_args)
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        # Anti-detection
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

    async def shutdown(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()

    async def scrape(self, url: str, wait_for: str = "networkidle", **kwargs) -> ScrapedData:
        if not self._context:
            await self.startup()

        page: Page = await self._context.new_page()
        try:
            resp = await page.goto(url, wait_until=wait_for, timeout=self.timeout * 1000)
            status = resp.status if resp else 0

            # Scroll to load lazy content
            await self._scroll_page(page)

            # Wait for dynamic content
            extra_wait = kwargs.get("extra_wait", 2)
            if extra_wait:
                await asyncio.sleep(extra_wait)

            html = await page.content()
            title = await page.title()

            # Extract data using same parser
            static = StaticScraper()
            data = static._parse(url, html, status, {})

            # Override title from actual page title
            if title:
                data.title = title

            # Intercept network requests for additional resources
            data.scripts = list(set(data.scripts))
            data.stylesheets = list(set(data.stylesheets))

            return data

        finally:
            await page.close()

    async def _scroll_page(self, page: Page, scroll_delay: float = 0.5, max_scrolls: int = 10):
        """Scroll page to trigger lazy loading."""
        last_height = await page.evaluate("document.body.scrollHeight")
        for _ in range(max_scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(scroll_delay)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height


class ScraperFactory:
    """Factory - auto-picks the right scraper strategy."""

    def __init__(self, proxy: str | None = None, headless: bool = True, timeout: int = 30):
        self.static = StaticScraper(proxy=proxy, timeout=timeout)
        self.headless = HeadlessScraper(proxy=proxy, headless=headless, timeout=timeout)

    async def scrape(self, url: str, mode: str = "auto", **kwargs) -> ScrapedData:
        """
        mode: 'static', 'headless', 'auto'
        auto tries static first, falls back to headless if JS-heavy.
        """
        if mode == "static":
            return await self.static.scrape(url, **kwargs)
        elif mode == "headless":
            return await self.headless.scrape(url, **kwargs)
        else:  # auto
            try:
                data = await self.static.scrape(url, **kwargs)
                # Heuristic: if very little text but has scripts, likely JS-rendered
                if len(data.text_content) < 200 and (data.scripts or "react" in data.html.lower() or "vue" in data.html.lower() or "next" in data.html.lower()):
                    return await self.headless.scrape(url, **kwargs)
                return data
            except Exception:
                return await self.headless.scrape(url, **kwargs)

    async def close(self):
        await self.headless.shutdown()
