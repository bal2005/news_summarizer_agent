import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
from newsapi import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException

load_dotenv()
logger = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not NEWS_API_KEY:
    raise RuntimeError("NEWS_API_KEY missing")

_newsapi = NewsApiClient(api_key=NEWS_API_KEY)

def fetch_news(
    query: str,
    page_size: int = 10,
    language: str = "en"
) -> List[Dict]:
    """
    Fetch news articles from NewsAPI.
    """
    try:
        response = _newsapi.get_everything(
            q=query,
            language=language,
            page_size=page_size
        )
        return response.get("articles", [])
    except NewsAPIException as e:
        logger.error(f"NewsAPI error: {e}")
        return []


def fetch_multiple_queries(
    queries: List[str],
    page_size: int = 10
) -> List[Dict]:
    """
    Fetch news for multiple queries and deduplicate by URL.
    """
    articles = []
    for q in queries:
        articles.extend(fetch_news(q, page_size=page_size))

    deduped = {a["url"]: a for a in articles if a.get("url")}
    return list(deduped.values())
