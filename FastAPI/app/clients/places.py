# Google Places (Nearby Search) client — just needs GOOGLE_PLACES_API_KEY,
# no OAuth, no browser step. Used for Flow A's venue search and Flow D's
# "popups near you" feed.

import requests

from app.config import GOOGLE_PLACES_API_KEY

NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


def search_places(query: str, lat: float, lng: float, radius_m: int = 3000) -> list[dict]:
    """Returns up to 5 {"name", "address", "rating"} results near (lat, lng)."""
    if not GOOGLE_PLACES_API_KEY:
        raise RuntimeError(
            "GOOGLE_PLACES_API_KEY is not set. Enable the Places API and create an API "
            "key in Google Cloud Console, then put it in .env."
        )

    response = requests.get(
        NEARBY_SEARCH_URL,
        params={
            "keyword": query,
            "location": f"{lat},{lng}",
            "radius": radius_m,
            "key": GOOGLE_PLACES_API_KEY,
        },
    )
    response.raise_for_status()
    data = response.json()
    return [
        {"name": r.get("name"), "address": r.get("vicinity"), "rating": r.get("rating")}
        for r in data.get("results", [])[:5]
    ]
