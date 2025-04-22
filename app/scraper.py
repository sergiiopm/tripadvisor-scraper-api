import re
import json
import time
import logging
from typing import List, Dict
from urllib.parse import urljoin

from playwright.async_api import async_playwright
import asyncio

# ─── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─── Constantes ────────────────────────────────────────────────────
BASE_DOMAIN = "https://www.tripadvisor.es"
VIEWPORT = {"width": 1280, "height": 800}


async def obtener_html_con_playwright(url: str) -> str:
    url = str(url)
    logger.info(f"[Playwright] Navegando a {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport=VIEWPORT,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36"
            ),
            locale="es-ES"
        )
        page = await context.new_page()
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle")
        html = await page.content()
        await browser.close()
    logger.info(f"[Playwright] HTML obtenido ({len(html)} car.)")
    return html


def extract_page_manifest(html: str) -> Dict:
    logger.info("Buscando pageManifest en el HTML…")
    m = re.search(r"pageManifest\s*:\s*(\{.+?\});", html, re.DOTALL)
    if not m:
        logger.error("No se encontró pageManifest.")
        raise RuntimeError("pageManifest not found")
    data = json.loads(m.group(1))
    logger.info("pageManifest parseado OK.")
    return data


def parse_reviews_from_manifest(manifest: Dict) -> List[Dict]:
    reviews = []
    for sec, content in manifest.items():
        if isinstance(content, dict) and "listResults" in content:
            items = content["listResults"]
            logger.info(f"Extrayendo {len(items)} reseñas de sección `{sec}`")
            for it in items:
                reviews.append({
                    "user": it.get("userDisplayName"),
                    "avatar_url": it.get("userProfile", {}).get("avatarUrl"),
                    "rating": it.get("rating"),
                    "title": it.get("title"),
                    "description": it.get("text"),
                    "review_url": urljoin(BASE_DOMAIN, it.get("url", "")),
                    "review_id": it.get("reviewId"),
                })
    logger.info(f"Total reseñas extraídas: {len(reviews)}")
    return reviews


async def scraper_tripadvisor(start_url: str, delay: float = 2.0) -> List[Dict]:
    start_url = str(start_url)
    logger.info(f"Iniciando scraper para: {start_url}")
    html = await obtener_html_con_playwright(start_url)
    manifest = extract_page_manifest(html)
    reviews = parse_reviews_from_manifest(manifest)

    # si quieres paginar, podrías:
    # next_url = manifest.get("properties", {}) \
    #     .get("pagination", {}).get("nextUrl")
    # if next_url:
    #     await asyncio.sleep(delay)
    #     reviews += await scraper_tripadvisor(next_url, delay)

    return reviews
