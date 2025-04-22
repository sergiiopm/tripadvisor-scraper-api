from pydantic import BaseModel, HttpUrl
from typing import List, Optional

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
