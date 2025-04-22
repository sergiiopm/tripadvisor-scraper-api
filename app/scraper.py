import re
import json
import time
import random
import logging

from typing import List, Dict
from urllib.parse import urljoin

import httpx

# ─── Configuración de logging ─────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─── Constantes ────────────────────────────────────────────────────
BASE_DOMAIN = "https://www.tripadvisor.es"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36",
]

def fetch_html(url: str) -> str:
    """
    Descarga la página usando HTTP/2 y un User‑Agent aleatorio.
    """
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "es-ES,es;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    logger.info(f"GET (HTTP/2) {url}")
    with httpx.Client(http2=True, headers=headers, timeout=15) as client:
        resp = client.get(url)
        logger.info(f"→ Status code: {resp.status_code}")
        resp.raise_for_status()
        return resp.text

def extract_page_manifest(html: str) -> Dict:
    """
    Extrae el objeto JavaScript `pageManifest:{ ... };` y lo devuelve como dict.
    """
    logger.info("Buscando pageManifest en el HTML...")
    m = re.search(r"pageManifest\s*:\s*(\{.+?\});", html, re.DOTALL)
    if not m:
        logger.error("No se encontró pageManifest en la página.")
        raise RuntimeError("pageManifest not found")
    manifest_json = m.group(1)
    data = json.loads(manifest_json)
    logger.info("pageManifest parseado correctamente.")
    return data

def parse_reviews_from_manifest(manifest: Dict) -> List[Dict]:
    """
    Recorre el manifest y extrae las reseñas encontradas en cualquier sección
    que incluya la clave 'listResults'.
    """
    reviews = []
    for section_name, section in manifest.items():
        if isinstance(section, dict) and "listResults" in section:
            items = section["listResults"]
            logger.info(f"Extrayendo {len(items)} reseñas de la sección '{section_name}'")
            for item in items:
                reviews.append({
                    "user": item.get("userDisplayName"),
                    "avatar_url": item.get("userProfile", {}).get("avatarUrl"),
                    "rating": item.get("rating"),
                    "title": item.get("title"),
                    "description": item.get("text"),
                    "review_url": urljoin(BASE_DOMAIN, item.get("url", "")),
                    "review_id": item.get("reviewId"),
                })
    logger.info(f"Total reviews extraídas: {len(reviews)}")
    return reviews

def scraper_tripadvisor(start_url: str, delay: float = 2.0) -> List[Dict]:
    """
    Dada la URL de la ficha de Tripadvisor, descarga la página,
    extrae el pageManifest y devuelve la lista de reseñas.
    """
    start_url = str(start_url)
    logger.info(f"Iniciando scraper para: {start_url}")

    html = fetch_html(start_url)
    manifest = extract_page_manifest(html)
    reviews = parse_reviews_from_manifest(manifest)

    # Opcional: si quieres paginar, podrías leer en manifest:
    # next_url = manifest.get("properties", {}).get("pagination", {}).get("nextUrl")
    # if next_url:
    #     time.sleep(delay)
    #     reviews += scraper_tripadvisor(urljoin(BASE_DOMAIN, next_url), delay)

    return reviews
