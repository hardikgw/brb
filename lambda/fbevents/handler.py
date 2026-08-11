import json
import logging
import os
import time
import urllib.parse
import urllib.request

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
_GRAPH_VERSION = os.environ.get("FB_GRAPH_VERSION", "v21.0")
_CACHE_SECONDS = int(os.environ.get("FB_CACHE_SECONDS", "1800"))
_LIMIT = int(os.environ.get("FB_EVENTS_LIMIT", "10"))

# Whitelist of fields requested from Graph API; the response is re-shaped
# below so the client never sees raw Graph payloads.
_FIELDS = "id,name,start_time,end_time,place,cover{source},is_canceled"

# Warm-container cache so repeat hits don't call Graph API. CloudFront-less
# clients also get a Cache-Control so browsers reuse the response.
_cache: dict = {"at": 0.0, "body": None}

_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Cache-Control": f"public, max-age={_CACHE_SECONDS}",
}


def _response(body: str) -> dict:
    return {"statusCode": 200, "headers": _HEADERS, "body": body}


def _fetch_events() -> list[dict]:
    query = urllib.parse.urlencode({
        "fields": _FIELDS,
        "time_filter": "upcoming",
        "limit": str(_LIMIT),
        "access_token": _PAGE_TOKEN,
    })
    url = f"https://graph.facebook.com/{_GRAPH_VERSION}/{_PAGE_ID}/events?{query}"
    with urllib.request.urlopen(url, timeout=8) as res:
        payload = json.load(res)

    events = []
    for ev in payload.get("data", []):
        if ev.get("is_canceled") or not ev.get("id"):
            continue
        events.append({
            "name": ev.get("name"),
            "startTime": ev.get("start_time"),
            "endTime": ev.get("end_time"),
            "place": (ev.get("place") or {}).get("name"),
            "cover": (ev.get("cover") or {}).get("source"),
            "url": f"https://www.facebook.com/events/{ev['id']}",
        })
    events.sort(key=lambda e: e.get("startTime") or "")
    return events


def lambda_handler(event, context):
    if not (_PAGE_ID and _PAGE_TOKEN):
        logger.warning("FB_PAGE_ID/FB_PAGE_TOKEN not set — returning empty list")
        return _response(json.dumps({"configured": False, "events": []}))

    now = time.time()
    if _cache["body"] is not None and now - _cache["at"] < _CACHE_SECONDS:
        return _response(_cache["body"])

    try:
        body = json.dumps({"configured": True, "events": _fetch_events()})
        _cache.update(at=now, body=body)
        return _response(body)
    except Exception:
        logger.exception("Failed to fetch Facebook events")
        if _cache["body"] is not None:
            # Serve stale rather than nothing while Graph API is unhappy.
            return _response(_cache["body"])
        return _response(json.dumps({"configured": True, "events": [], "error": True}))
