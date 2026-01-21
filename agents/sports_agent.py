# agents/sports_agent.py

import os
import json
import re
import logging
from typing import List, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
from dotenv import load_dotenv
from newsapi import NewsApiClient
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from dateutil import parser as date_parser

# ------------------------------------------------------
# Logging
# ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | sports_agent | %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------
# Environment
# ------------------------------------------------------
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

newsapi = NewsApiClient(api_key=NEWS_API_KEY)
llm = ChatOllama(model="llama3.1:8b", temperature=0)

# ------------------------------------------------------
# Config
# ------------------------------------------------------
TEAM = "Australia"
SPORT = "Cricket"   # Cricket | Football

MAX_NEWSAPI = 10
MAX_RSS = 10
FINAL_ARTICLES = 5
MAX_LLM_WORKERS = 5

# ------------------------------------------------------
# RSS Feeds
# ------------------------------------------------------
CRICKET_RSS = [
    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
]

FOOTBALL_RSS = [
    "https://www.espn.com/espn/rss/soccer/news",
    "https://www.goal.com/feeds/news"
]

def get_rss_feeds() -> List[str]:
    if SPORT.lower() == "cricket":
        return CRICKET_RSS
    if SPORT.lower() == "football":
        return FOOTBALL_RSS
    return []

# ------------------------------------------------------
# Prompts
# ------------------------------------------------------
QUERY_PROMPT = PromptTemplate.from_template("""
Generate 5 short search queries for NewsAPI.

Rules:
- Focus only on {TEAM} {SPORT}
- No boolean operators
- 2–3 words each
Return ONLY a JSON array.
""")

CLASSIFY_PROMPT = PromptTemplate.from_template("""
Is this article related to {TEAM} {SPORT}?

Answer ONLY YES or NO.

Title: {title}
Content: {content}
""")

SUMMARY_PROMPT = PromptTemplate.from_template("""
Summarize EACH sports news item separately and return as a list of bullet points.

Context:
- Team: {TEAM}
- Sport: {SPORT}

Rules:
- EXACTLY one bullet per article
- Each bullet must describe a DIFFERENT news event
- NO intro, NO explanation, NO meta text
- NO grouping of articles
- NO phrases like "here is", "this article", "the following"
- Focus on:
  match results, injuries, squad changes, playing XI, tactics

Eg:
🏏 Sports
Summary:
• Sam Harper was named Big Bash League Player of the Season after a career-best campaign.
• Mitchell overtook Virat Kohli to become the world’s top-ranked men’s ODI batter.
• Hobart Hurricanes confirmed their captain will miss the BBL knockout final due to injury.
• Perth Scorchers and Sydney Sixers are set to face off in the BBL Qualifier.
• Team selections were influenced by player availability ahead of the knockout stage.

Sam Harper named player of the BBL after career-best season
Mitchell goes past Kohli to become top men's ODI batter
Hobart loses skipper for BBL knockout final
Perth Scorchers vs Sydney Sixers Qualifier preview
BBL teams finalize lineups for knockout stage                                            

Articles:
{articles}
""")

# ------------------------------------------------------
# Helpers
# ------------------------------------------------------
def parse_date_safe(date_str: str):
    try:
        return date_parser.parse(date_str)
    except Exception:
        return datetime.min


def normalize_article(a: Dict, source: str) -> Dict:
    return {
        "title": a.get("title", "").strip(),
        "summary": a.get("summary") or a.get("description", ""),
        "url": a.get("url") or a.get("link"),
        "published": a.get("publishedAt") or a.get("published"),
        "source": source
    }


# ------------------------------------------------------
# Query Generation
# ------------------------------------------------------
def generate_queries() -> List[str]:
    res = llm.invoke(QUERY_PROMPT.format(TEAM=TEAM, SPORT=SPORT))
    match = re.search(r"\[.*\]", res.content, re.DOTALL)

    if match:
        try:
            queries = json.loads(match.group())
            if queries:
                return queries
        except Exception:
            pass

    fallback = [f"{TEAM} {SPORT} news"]
    logger.warning(f"Using fallback query: {fallback}")
    return fallback


# ------------------------------------------------------
# Fetch NewsAPI
# ------------------------------------------------------
def fetch_newsapi_articles(queries: List[str]) -> List[Dict]:
    articles = []

    for q in queries:
        try:
            logger.info(f"NewsAPI query: {q}")
            res = newsapi.get_everything(
                q=q,
                language="en",
                sort_by="publishedAt",
                page_size=MAX_NEWSAPI
            )
            for a in res.get("articles", []):
                articles.append(normalize_article(a, "newsapi"))
        except Exception as e:
            logger.error(f"NewsAPI error for '{q}': {e}")

    logger.info(f"Fetched {len(articles)} NewsAPI articles")
    return articles[:MAX_NEWSAPI]


# ------------------------------------------------------
# Fetch RSS (Mandatory)
# ------------------------------------------------------
def fetch_rss_articles() -> List[Dict]:
    feeds = get_rss_feeds()
    articles = []

    for feed_url in feeds:
        logger.info(f"Fetching RSS: {feed_url}")
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:MAX_RSS]:
            articles.append(normalize_article({
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "link": entry.get("link"),
                "published": entry.get("published")
            }, "rss"))

    logger.info(f"Fetched {len(articles)} RSS articles")
    return articles


# ------------------------------------------------------
# LLM Classification
# ------------------------------------------------------
def classify_article(article: Dict) -> bool:
    res = llm.invoke(CLASSIFY_PROMPT.format(
        TEAM=TEAM,
        SPORT=SPORT,
        title=article["title"],
        content=article["summary"]
    ))
    return res.content.strip().upper().startswith("YES")


# ------------------------------------------------------
# Summarization
# ------------------------------------------------------
def summarize_articles(articles: List[Dict]) -> str:
    content = "\n".join(
        f"{idx+1}. {a['title']}"
        for idx, a in enumerate(articles)
    )

    res = llm.invoke(SUMMARY_PROMPT.format(
        TEAM=TEAM,
        SPORT=SPORT,
        articles=content
    ))
    return res.content.strip()


# ------------------------------------------------------
# AGENT ENTRY
# ------------------------------------------------------
def run_sports_agent() -> Dict:
    logger.info("🏏 Sports agent started")

    queries = generate_queries()

    newsapi_articles = fetch_newsapi_articles(queries)
    rss_articles = fetch_rss_articles()   # ✅ mandatory

    # Combine + deduplicate
    combined = {}
    for a in newsapi_articles + rss_articles:
        if a["url"]:
            combined[a["url"]] = a

    articles = list(combined.values())

    # Sort by recency
    articles.sort(
        key=lambda x: parse_date_safe(x.get("published")),
        reverse=True
    )

    # Parallel classification
    relevant = []
    with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as exe:
        futures = {exe.submit(classify_article, a): a for a in articles}
        for f in as_completed(futures):
            if f.result():
                relevant.append(futures[f])

    final_articles = relevant[:FINAL_ARTICLES]
    logger.info(f"Final sports articles selected: {len(final_articles)}")

    if not final_articles:
        logger.warning("No relevant sports news found")
        return {}

    return {
        "title": "🏏 Sports News",
        "summary": summarize_articles(final_articles),
        "articles": final_articles
    }
