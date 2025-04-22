import re
import time
import logging
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

async def parsear_pagina(html: str) -> List[Dict]:
    """
    Dado el HTML completo de una página de Tripadvisor, extrae todas
    las reseñas con BeautifulSoup.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", {"data-automation": "reviewCard"})
    logger.info(f"→ Encontradas {len(cards)} reseñas en la página")
    reviews = []

    for idx, card in enumerate(cards, start=1):
        # Usuario y avatar
        user = avatar_url = None
        perfiles = card.find_all("a", href=re.compile(r"^/Profile/"))
        for p in perfiles:
            img = p.find("img")
            if img and img.has_attr("src"):
                avatar_url = img["src"]
            else:
                user = p.get_text(strip=True)

        # Rating
        rating = None
        svg = card.find("svg", {"data-automation": "bubbleRatingImage"})
        if svg and (t := svg.find("title")):
            rating = int(float(t.get_text(strip=True).split()[0]))

        # Título, enlace e ID
        title = review_url = review_id = None
        tc = card.find("div", {"data-test-target": "review-title"})
        if tc and (a := tc.find("a", href=True)):
            title = a.get_text(strip=True)
            review_url = urljoin(BASE_DOMAIN, a["href"])
            if m := re.search(r"-r(\d+)-", a["href"]):
                review_id = m.group(1)

        # Descripción
        description = None
        body = card.find("div", {"data-test-target": "review-body"})
        if body and (span := body.find("span", class_=re.compile(r"JguWG"))):
            description = span.get_text(strip=True)

        logger.debug(f"Review {idx}: user={user!r}, rating={rating}, id={review_id}")
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
    """
    Abre Playwright, recorre todas las páginas de reseñas clicando
    "siguiente", y acumula todas las reviews en una lista.
    """
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
            html = await page.content()
            logger.info(f"[Playwright] HTML obtenido ({len(html)} caracteres)")

            # Parsear y acumular
            reviews = await parsear_pagina(html)
            if not reviews:
                logger.info("No hay reviews en esta página, deteniendo.")
                break
            all_reviews.extend(reviews)

            # Intentar clicar 'siguiente'
            try:
                next_button = await page.query_selector(
                    'a[data-smoke-attr="pagination-next-arrow"]'
                )
                if not next_button:
                    logger.info("No hay botón 'Página siguiente', fin de paginación.")
                    break
                # Obtener href y construir URL completa
                href = await next_button.get_attribute("href")
                if not href:
                    break
                next_url = urljoin(BASE_DOMAIN, href)
                logger.info(f"Next page URL: {next_url}")
                page_num += 1
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Error en paginación: {e}")
                break

        await browser.close()

    logger.info(f"Scraping completado: {len(all_reviews)} reseñas totales.")
    return all_reviews
