from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from .scraper import scraper_tripadvisor

class ScrapeRequest(BaseModel):
    url: HttpUrl

class Review(BaseModel):
    user: Optional[str]
    avatar_url: Optional[HttpUrl]
    rating: Optional[int]
    title: Optional[str]
    description: Optional[str]
    review_url: Optional[HttpUrl]
    review_id: Optional[str]

class ScrapeResponse(BaseModel):
    reviews: List[Review]

app = FastAPI(title="TripAdvisor Scraper API")

@app.post("/scrape", response_model=ScrapeResponse)
def scrape_endpoint(req: ScrapeRequest):
    try:
        data = scraper_tripadvisor(req.url)
        return ScrapeResponse(reviews=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
