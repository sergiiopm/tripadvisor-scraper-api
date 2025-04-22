from fastapi import FastAPI, HTTPException
from .models import ScrapeRequest, ScrapeResponse   # aquí falla porque no existe app/models.py
from .scraper import scraper_tripadvisor

app = FastAPI(title="TripAdvisor Scraper API")

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(req: ScrapeRequest):
    url_str = str(req.url)
    try:
        reviews = scraper_tripadvisor(url_str)
        return ScrapeResponse(reviews=reviews)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
