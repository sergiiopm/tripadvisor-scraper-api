import re
import json
import time
import logging
from typing import List, Dict
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

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

def obtener_html_con_playwright(url: str) -> str:
    """
    Lanza un Chromium headless con Playwright, navega a la URL y devuelve
    el HTML renderizado (incluyendo el <script> con pageManifest).
    """
    url = str(url)
    logger.info(f"[Playwright] Navegando a {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-setuid-sandbox"
        ])
        context = browser.new_context(
            viewport=VIEWPORT,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36"
            ),
            locale="es-ES"
        )
        page = context.new_page()
        page.goto(url, timeout=30000)
        # Espera a que cargue el script de TripAdvisor (script[type="application/json"] u otro)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()
    logger.info(f"[Playwright] HTML obtenido ({len(html)} caracteres)")
    return html

def extract_page_manifest(html: str) -> Dict:
    """
    Extrae el objeto JavaScript `pageManifest: {...};` y lo devuelve como dict.
    """
    logger.info("Buscando pageManifest en el HTML...")
    m = re.search(r"pageManifest\s*:\s*(\{.+?\});", html, re.DOTALL)
    if not m:
        logger.error("No se encontró pageManifest en la página.")
        raise RuntimeError("pageManifest not found")
    data = json.loads(m.group(1))
    logger.info("pageManifest parseado correctamente.")
    return data

def parse_reviews_from_manifest(manifest: Dict) -> List[Dict]:
    """
    Recorre el manifest y extrae todas las reseñas
    de las secciones que incluyan 'listResults'.
    """
    reviews = []
    for section, content in manifest.items():
        if isinstance(content, dict) and "listResults" in content:
            items = content["listResults"]
            logger.info(f"Extrayendo {len(items)} reseñas de sección `{section}`")
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
    logger.info(f"Total reseñas extraídas: {len(reviews)}")
    return reviews

def scraper_tripadvisor(start_url: str, delay: float = 2.0) -> List[Dict]:
    """
    Dada la URL de TripAdvisor, abre con Playwright, extrae el JSON
    de pageManifest y devuelve todas las reseñas encontradas.
    """
    start_url = str(start_url)

    logger.info(f"Iniciando scraper para: {start_url}")
    # 1) Obtenemos el HTML renderizado
    html = obtener_html_con_playwright(start_url)
    # 2) Sacamos el manifest
    manifest = extract_page_manifest(html)
    # 3) Parseamos reseñas
    reviews = parse_reviews_from_manifest(manifest)
    # 4) Si hubiera paginación en el manifest, podrías recursar aquí
    #    por ejemplo leyendo manifest["properties"]["pagination"]["nextUrl"]
    return reviews
