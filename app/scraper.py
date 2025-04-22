import random
import re
import time
import logging
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup

# ─── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─── Constantes ────────────────────────────────────────────────────
BASE_DOMAIN = "https://www.tripadvisor.es"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
]

# Creamos un cloudscraper «base»
scraper = cloudscraper.create_scraper()

def obtener_sopa(url: str) -> BeautifulSoup:
    """Descarga la página e informa por logging."""
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "es-ES,es;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }

    logger.info(f"Fetching URL: {url}")
    logger.debug(f"Headers: {headers}")

    try:
        resp = scraper.get(url, headers=headers, timeout=15)
        logger.info(f"→ Status code: {resp.status_code}")
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        raise

def parsear_pagina(soup: BeautifulSoup) -> list[dict]:
    """Extrae todas las reseñas de la página actual."""
    cards = soup.find_all("div", {"data-automation": "reviewCard"})
    logger.info(f"Found {len(cards)} review cards on this page")
    reviews = []

    for idx, card in enumerate(cards, start=1):
        # --- Usuario y avatar ---
        user = None
        avatar_url = None
        perfiles = card.find_all("a", href=re.compile(r"^/Profile/"))
        for p in perfiles:
            img = p.find("img")
            if img and img.has_attr("src"):
                avatar_url = img["src"]
            else:
                user = p.get_text(strip=True)

        # --- Rating ---
        rating = None
        svg = card.find("svg", {"data-automation": "bubbleRatingImage"})
        if svg and (t := svg.find("title")):
            rating = int(float(t.get_text(strip=True).split()[0]))

        # --- Título, enlace e ID ---
        title = review_url = review_id = None
        tc = card.find("div", {"data-test-target": "review-title"})
        if tc and (a := tc.find("a", href=True)):
            title = a.get_text(strip=True)
            review_url = urljoin(BASE_DOMAIN, a["href"])
            if m := re.search(r"-r(\d+)-", a["href"]):
                review_id = m.group(1)

        # --- Descripción ---
        description = None
        body = card.find("div", {"data-test-target": "review-body"})
        if body and (span := body.find("span", class_=re.compile(r"JguWG"))):
            description = span.get_text(strip=True)

        logger.debug(
            f"Review {idx}: user={user!r}, rating={rating}, review_id={review_id}"
        )

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

def scraper_tripadvisor(start_url: str, delay: float = 2.0) -> list[dict]:
    """
    Recorre todas las páginas de reseñas e imprime logs de cada paso.
    """
    # Forzamos que start_url sea str, no HttpUrl u otro tipo
    start_url = str(start_url)
    logger.info(f"Starting scraper for: {start_url}")

    all_reviews = []
    next_page = start_url
    page = 1

    while next_page:
        logger.info(f"=== Page {page} ===")
        soup = obtener_sopa(next_page)
        bloque = parsear_pagina(soup)
        if not bloque:
            logger.info("No reviews found on this page, stopping.")
            break
        all_reviews.extend(bloque)

        # Paginación
        nxt = soup.find("a", {"data-smoke-attr": "pagination-next-arrow"})
        if nxt and nxt.has_attr("href"):
            next_page = urljoin(BASE_DOMAIN, nxt["href"])
            logger.info(f"Next page URL: {next_page}")
            page += 1
            time.sleep(delay)
        else:
            logger.info("No next page link found, finished pagination.")
            break

    logger.info(f"Finished scraping. Total reviews: {len(all_reviews)}")
    return all_reviews
