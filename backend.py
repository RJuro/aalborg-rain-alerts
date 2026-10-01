"""Server-side client: n8n owns forecasts, subscriptions, and email delivery."""
from datetime import datetime, timezone
import re
import secrets
from urllib.parse import urlparse
import requests

DEFAULT_BASE_URL = "https://n8n.automate.business.aau.dk"
EMAIL = re.compile(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$", re.I)

class BackendError(Exception):
    """A safe message that may be displayed to a visitor."""

def normalize_email(value):
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL.fullmatch(email):
        raise BackendError("Please enter a valid email address.")
    return email

def api_url(base_url, route):
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise BackendError("The weather service is not configured correctly.")
    return base_url.rstrip("/") + "/webhook/" + route

def _request(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=(5, 30), **kwargs)
        if response.status_code == 429:
            raise BackendError("Please wait a few minutes before trying again.")
        if not response.ok:
            raise BackendError("The service is temporarily unavailable. Please try again shortly.")
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise BackendError("The service is temporarily unavailable. Please try again shortly.") from exc
    if not isinstance(data, dict):
        raise BackendError("The service returned an incomplete response.")
    return data

def fetch_weather(base_url=DEFAULT_BASE_URL):
    data = _request("GET", api_url(base_url, "aalborg-weather-v1"))
    try:
        fetched = datetime.fromisoformat(data["fetched_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        valid = (
            fetched.tzinfo is not None and -60 <= age <= 1800
            and data["city"] == "Aalborg"
            and isinstance(data["rain_likely"], bool)
            and 0 <= data["max_hourly_probability"] <= 100
            and isinstance(data["hours"], list) and len(data["hours"]) >= 6
            and all(
                h["start"] and h["end"]
                and (h["probability"] is None or 0 <= h["probability"] <= 100)
                and (h["rain_mm"] is None or h["rain_mm"] >= 0)
                for h in data["hours"]
            )
        )
        for key in ("threshold_percent", "horizon_hours", "cooldown_hours", "minimum_rain_mm"):
            valid = valid and isinstance(data[key], (int, float)) and data[key] > 0
        if data["rain_likely"]:
            valid = valid and bool(data["first_rain_start"])
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise BackendError("A fresh, complete forecast is unavailable. Please check back shortly.")
    return data

def subscribe(email, consent, base_url=DEFAULT_BASE_URL):
    email = normalize_email(email)
    if consent is not True:
        raise BackendError("Please agree to receive rain alert emails.")
    data = _request(
        "POST", api_url(base_url, "aalborg-rain-subscribe-v1"),
        json={
            "email": email, "consent": True,
            "confirm_token": secrets.token_urlsafe(32),
            "unsubscribe_token": secrets.token_urlsafe(32),
        },
    )
    if data.get("ok") is not True:
        raise BackendError("Your signup could not be completed. Please try again shortly.")
    return data.get("message", "Check your inbox for a confirmation link.")

