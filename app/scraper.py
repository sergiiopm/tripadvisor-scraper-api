import re
import time
import logging
import asyncio
from typing import List, Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page

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
REVIEW_CARD_SELECTOR = 'div[data-automation="reviewCard"]'
NEXT_BUTTON_SELECTOR = 'a[data-smoke-attr="pagination-next-arrow"]'
COOKIE_ACCEPT_BUTTON = '#onetrust-accept-btn-handler'  # id estándar del banner de cookies

async def parsear_pagina(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(REVIEW_CARD_SELECTOR)
    logger.info(f"→ Encontradas {len(cards)} reseñas en la página")
    reviews = []

    for idx, card in enumerate(cards, start=1):
        user = avatar_url = None
        for p in card.select('a[href^="/Profile/"]'):
            img = p.find("img")
            if img and img.has_attr("src"):
                avatar_url = img["src"]
            else:
                user = p.get_text(strip=True)

        rating = None
        if (svg := card.select_one('svg[data-automation="bubbleRatingImage"]')):
            if (t := svg.find("title")):
                rating = int(float(t.get_text(strip=True).split()[0]))

        title = review_url = review_id = None
        if (a := card.select_one('div[data-test-target="review-title"] a[href]')):
            title = a.get_text(strip=True)
            review_url = urljoin(BASE_DOMAIN, a["href"])
            if m := re.search(r"-r(\d+)-", a["href"]):
                review_id = m.group(1)

        description = None
        if (span := card.select_one('div[data-test-target="review-body"] span.JguWG')):
            description = span.get_text(strip=True)

        reviews.append({
            "user": user,
            "avatar_url": avatar_url,
            "rating": rating,
            "title": title,
            "description": description,
            "review_url": review_url,
            "review_id": review_id,
        })

    return reviews

async def scraper_tripadvisor(start_url: str, delay: float = 2.0) -> List[Dict]:
    start_url = str(start_url)
    logger.info(f"Iniciando scraper (Playwright) para: {start_url}")

    all_reviews: List[Dict] = []
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
        page: Page = await context.new_page()
        next_url = start_url
        page_num = 1

        while next_url:
            logger.info(f"=== Página {page_num} ===")
            await page.goto(next_url, timeout=30000)
            await page.wait_for_load_state("networkidle")

            # 1) Cerrar banner de cookies si existe
            try:
                btn = await page.query_selector(COOKIE_ACCEPT_BUTTON)
                if btn:
                    await btn.click()
                    logger.info("Banner de cookies aceptado")
                    await asyncio.sleep(1)
            except Exception:
                pass

            # 2) Scroll “fuerte” para cargar reseñas diferidas
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            # 3) Esperar a que el selector de reseñas aparezca
            try:
                await page.wait_for_selector(REVIEW_CARD_SELECTOR, timeout=15000)
            except Exception:
                logger.warning("Sigue sin aparecer ninguna reseña tras scroll")

            html = await page.content()
            logger.info(f"[Playwright] HTML obtenido ({len(html)} caracteres)")
            reviews = await parsear_pagina(html)

            if not reviews:
                logger.info("No hay reviews en esta página, deteniendo.")
                break
            all_reviews.extend(reviews)

            # 4) Paginación: siguiente
            elem = await page.query_selector(NEXT_BUTTON_SELECTOR)
            if not elem:
                logger.info("No hay botón 'Página siguiente'; fin de paginación.")
                break
            href = await elem.get_attribute("href")
            if not href:
                break
            next_url = urljoin(BASE_DOMAIN, href)
            logger.info(f"Next page URL: {next_url}")
            page_num += 1
            await asyncio.sleep(delay)

        await browser.close()

    logger.info(f"Scraping completado: {len(all_reviews)} reseñas totales.")
    return all_reviews
