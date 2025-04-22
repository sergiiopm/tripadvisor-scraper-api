import time
import re
import logging
from typing import List, Dict

import httpx
from bs4 import BeautifulSoup

# ─── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def scraper_tripadvisor(start_url: str, delay: float = 1.0) -> List[Dict]:
    """
    Usa el endpoint OverlayWidgetAjax para recuperar todas las reseñas
    sin toparse la página principal ni pasar por DataDome.
    """
    # Extraemos el ID numérico de la ubicación de la URL
    m = re.search(r"-d(\d+)-", start_url)
    if not m:
        raise ValueError("No se pudo extraer el ID de la ubicación")
    location_id = m.group(1)

    base_ajax = "https://www.tripadvisor.es/OverlayWidgetAjax"
    reviews: List[Dict] = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/116.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Referer": start_url,
        "X-Requested-With": "XMLHttpRequest",
    }

    with httpx.Client(timeout=10) as client:
        for offset in range(0, 1000, 15):
            params = {
                "Mode": "EXPANDED_HOTEL_REVIEWS_RESPONSIVE",
                "HotelID": location_id,
                "ReviewsFilter": "ALL",
                "ReviewOffset": offset,
                "webMobile": "false",
            }
            logger.info(f"Fetching AJAX offset={offset}")
            resp = client.get(base_ajax, headers=headers, params=params)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select('div[data-automation="reviewCard"]')
            if not cards:
                logger.info("No quedan más reseñas (offset=%d)", offset)
                break

            for card in cards:
                user_el = card.select_one('a[href^="/Profile/"]')
                user = user_el.get_text(strip=True) if user_el else None
                avatar = card.select_one('a[href^="/Profile/"] img')
                avatar_url = avatar["src"] if avatar else None

                title_el = card.select_one('div[data-test-target="review-title"] a')
                title = title_el.get_text(strip=True) if title_el else None
                href = title_el["href"] if title_el else ""
                review_id = re.search(r"-r(\d+)-", href)
                review_id = review_id.group(1) if review_id else None

                rating_el = card.select_one(
                    'svg[data-automation="bubbleRatingImage"] title'
                )
                rating = (
                    int(float(rating_el.get_text(strip=True).split()[0]))
                    if rating_el else None
                )

                desc_el = card.select_one('div[data-test-target="review-body"] span.JguWG')
                description = desc_el.get_text(strip=True) if desc_el else None

                reviews.append({
                    "user": user,
                    "avatar_url": avatar_url,
                    "rating": rating,
                    "title": title,
                    "description": description,
                    "review_id": review_id,
                })

            time.sleep(delay)

    logger.info(f"Total reseñas obtenidas: {len(reviews)}")
    return reviews
