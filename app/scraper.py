import random
import re
import time
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup

BASE_DOMAIN = "https://www.tripadvisor.es"

# Lista de User‑Agents reales para rotar
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    # Puedes añadir más UAs si lo deseas
]

# Creamos un scraper de cloudscraper “base”
scraper = cloudscraper.create_scraper()

def obtener_sopa(url: str) -> BeautifulSoup:
    """
    Descarga la página con cloudscraper para evitar bloqueos 403,
    rotando User-Agent y con cabeceras adicionales.
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "es-ES,es;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }

    # Si tienes proxy configurado vía ENV vars, cloudscraper lo usará automáticamente.
    resp = scraper.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def parsear_pagina(soup: BeautifulSoup) -> list[dict]:
    """
    Extrae de una sopa BeautifulSoup todas las reseñas de la página actual.
    """
    reviews = []
    cards = soup.find_all("div", {"data-automation": "reviewCard"})
    for card in cards:
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

        # --- Rating (1-5) ---
        rating = None
        svg = card.find("svg", {"data-automation": "bubbleRatingImage"})
        if svg and (title := svg.find("title")):
            # "4 de 5 burbujas" → [0] = '4'
            rating = int(float(title.get_text(strip=True).split()[0]))

        # --- Título, enlace e ID ---
        title = None
        review_url = None
        review_id = None
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
    Recorre todas las páginas de reseñas de la URL dada y devuelve
    una lista de diccionarios con los campos:
    user, avatar_url, rating, title, description, review_url, review_id.
    """
    all_reviews = []
    next_page = start_url

    while next_page:
        soup = obtener_sopa(next_page)
        bloque = parsear_pagina(soup)
        if not bloque:
            break
        all_reviews.extend(bloque)

        # Buscamos enlace a la siguiente página
        nxt = soup.find("a", {"data-smoke-attr": "pagination-next-arrow"})
        if nxt and nxt.has_attr("href"):
            next_page = urljoin(BASE_DOMAIN, nxt["href"])
            time.sleep(delay)
        else:
            break

    return all_reviews
