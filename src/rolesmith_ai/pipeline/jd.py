import asyncio
import random
import re

from playwright.async_api import async_playwright


async def _fetch_url(url: str) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            # Random delay 1.5-3s
            await asyncio.sleep(random.uniform(1.5, 3.0))
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait a bit for JS to render the body
            await asyncio.sleep(random.uniform(1.5, 3.0))

            # Try to get innerText of body to avoid HTML tags
            text = await page.evaluate("document.body.innerText")
            return text
        except Exception:
            return None
        finally:
            await browser.close()


def fetch_jd(url: str, platform: str) -> str | None:
    if platform.lower() == "linkedin":
        return None

    try:
        text = asyncio.run(_fetch_url(url))
        if text:
            # Clean up whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()
    except Exception:
        pass
    return None
