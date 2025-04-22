import requests
from bs4 import BeautifulSoup
import cloudscraper
import os
import re
import time
from urllib.parse import urljoin

BASE_DOMAIN = "https://www.tripadvisor.es"

# Creamos un scraper de cloudscraper al inicio:
scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)
# Opcional: añade cabeceras extra
scraper.headers.update({
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.google.com/",
})

def scraper_tripadvisor(start_url: str, delay: float = 2.0):
    def obtener_sopa(url):
        """
        Descarga la página con cloudscraper para evitar bloqueos 403.
        """
        # Si tienes proxy configurado por ENV vars, cloudscraper lo usa automáticamente.
        resp = scraper.get(url, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def parsear_pagina(soup):
        reviews = []
        cards = soup.find_all("div", {"data-automation": "reviewCard"})
        for card in cards:
            # usuario y avatar
            user = None
            avatar_url = None
            perfiles = card.find_all("a", href=re.compile(r"^/Profile/"))
            for p in perfiles:
                img = p.find("img")
                if img and img.has_attr("src"):
                    avatar_url = img["src"]
                else:
                    user = p.get_text(strip=True)

            # rating
            rating = None
            svg = card.find("svg", {"data-automation": "bubbleRatingImage"})
            if svg and svg.find("title"):
                rating = int(float(svg.find("title").get_text(strip=True).split()[0]))

            # título, enlace e ID
            title = None
            review_url = None
            review_id = None
            tc = card.find("div", {"data-test-target": "review-title"})
            if tc and tc.find("a", href=True):
                a = tc.find("a", href=True)
                title = a.get_text(strip=True)
                review_url = urljoin(BASE_DOMAIN, a["href"])
                m = re.search(r"-r(\d+)-", a["href"])
                if m:
                    review_id = m.group(1)

            # descripción
            description = None
            body = card.find("div", {"data-test-target": "review-body"})
            if body and body.find("span", class_=re.compile(r"JguWG")):
                description = body.find("span", class_=re.compile(r"JguWG")).get_text(strip=True)

            reviews.append({
                "user": user,
                "avatar_url": avatar_url,
                "rating": rating,
                "title": title,
                "description": description,
                "review_url": review_url,
                "review_id": review_id
            })
        return reviews

    all_reviews = []
    next_page = start_url

    while next_page:
        soup = obtener_sopa(next_page)
        bloque = parsear_pagina(soup)
        if not bloque:
            break
        all_reviews.extend(bloque)
        nxt = soup.find("a", {"data-smoke-attr": "pagination-next-arrow"})
        if nxt and nxt.has_attr("href"):
            next_page = urljoin(BASE_DOMAIN, nxt["href"])
            time.sleep(delay)
        else:
            break

    return all_reviews
