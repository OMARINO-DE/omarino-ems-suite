#!/usr/bin/env python3
"""
Screenshot Capture Script for OMARINO EMS Suite

This script uses Playwright to capture screenshots of the webapp.

Installation:
    pip install playwright
    playwright install chromium

Usage:
    python scripts/capture-screenshots.py
"""

import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Use the live demo URL or local development
BASE_URL = os.environ.get("DEMO_URL", "https://ems-demo.omarino.net")
SCREENSHOTS_DIR = Path(__file__).parent.parent / "docs" / "screenshots"

PAGES = [
    {"name": "home", "path": "/", "title": "Home Dashboard"},
    {"name": "dashboard", "path": "/dashboard", "title": "Analytics Dashboard"},
    {"name": "timeseries", "path": "/timeseries", "title": "Time Series Data"},
    {"name": "forecasts", "path": "/forecasts", "title": "Forecasting"},
    {"name": "optimization", "path": "/optimization", "title": "Optimization"},
    {"name": "scheduler", "path": "/scheduler", "title": "Workflow Scheduler"},
]


async def capture_screenshots():
    print("🚀 Starting screenshot capture...\n")

    # Create screenshots directory if it doesn't exist
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = await context.new_page()

        for page_info in PAGES:
            try:
                print(f"📸 Capturing: {page_info['title']} ({page_info['path']})")

                url = f"{BASE_URL}{page_info['path']}"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Wait for page to be fully rendered
                await page.wait_for_load_state("load", timeout=10000)
                
                # Wait for content to load and animations to complete
                await asyncio.sleep(4)

                screenshot_path = SCREENSHOTS_DIR / f"{page_info['name']}.png"
                await page.screenshot(path=str(screenshot_path), full_page=False, type='png')

                print(f"   ✅ Saved: {screenshot_path}\n")

            except Exception as e:
                print(f"   ❌ Failed to capture {page_info['title']}: {str(e)}\n")

        await browser.close()

    print("✨ Screenshot capture complete!")
    print(f"📁 Screenshots saved to: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
