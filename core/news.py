# core/news.py
import time, html, xml.etree.ElementTree as ET
from typing import List, Dict, Any
import requests

FEED = "https://www.bing.com/news/search?q=Top+news&format=rss"

_cache = {"ts": 0, "items": []}

def get_news(max_items: int = 10) -> List[Dict[str, Any]]:
    now = time.time()
    if now - _cache["ts"] < 180:  # cache 3 minutes
        return _cache["items"]

    try:
        r = requests.get(FEED, timeout=8)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("{http://purl.org/dc/elements/1.1/}date") or
                   item.findtext("pubDate") or "").strip()
            desc = (item.findtext("description") or "").strip()
            items.append({
                "title": html.unescape(title),
                "url": link,
                "published": pub,
                "summary": html.unescape(desc),
            })
        _cache.update({"ts": now, "items": items})
    except Exception:
        pass
    return _cache["items"]
