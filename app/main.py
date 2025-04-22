from fastapi import FastAPI, HTTPException
from .models import ScrapeRequest, ScrapeResponse
from .scraper import scraper_tripadvisor

app = FastAPI()

@app.post("/scrape", response_model=ScrapeResponse)
def scrape_endpoint(req: ScrapeRequest):
    try:
        data = scraper_tripadvisor(str(req.url))
        return ScrapeResponse(reviews=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
