# agents/finance_agent.py

import os
import json
import logging
import re
import requests
from typing import List, Dict
from datetime import datetime

import pandas as pd
import feedparser
from dotenv import load_dotenv
from newsapi import NewsApiClient
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from dateutil import parser as date_parser

# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | finance_agent | %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------------
# Environment
# ------------------------------
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
STOCK_API_KEY = os.getenv("STOCK_API_KEY")

# ------------------------------
# Clients
# ------------------------------
newsapi = NewsApiClient(api_key=NEWS_API_KEY)
llm = ChatOllama(model="llama3.1:8b", temperature=0)

# ------------------------------
# Constants
# ------------------------------
SECTOR = "Technology"
STOCK = "Infosys"
CSV_PATH = os.path.join(os.path.dirname(__file__), "nse_symbols.csv")

MAX_NEWSAPI = 10
MAX_RSS = 10
FINAL_ARTICLES = 5

FINANCE_RSS_FEED = "https://www.moneycontrol.com/rss/latestnews.xml"

# ------------------------------
# Prompts
# ------------------------------
QUERY_PROMPT = PromptTemplate.from_template("""
Generate 5 short search queries for NewsAPI for financial news.

Rules:
- No boolean operators
- Simple human phrases
- Focus on sector: {SECTOR} and stock: {STOCK}
- Mandatory to include the word stock
- 2-3 words each
Return ONLY a JSON array
""")

SUMMARY_PROMPT = PromptTemplate.from_template("""
Summarize EACH of the following finance news articles separately and return as a list of bulletin points.

Context:
- Sector: {SECTOR}
- Stock: {STOCK}

Rules:
- One point per article
- EXACTLY one bullet per article
- Each bullet must describe a DIFFERENT news event
- NO intro, NO explanation, NO meta text
- NO grouping of articles
- NO phrases like "here is", "this article", "the following"
- Focus on stock movement, earnings, deals, regulation, sector impact
- No inferred relationships
- Mention entity names only if present
                                              
Eg:
💰 Finance
Summary:
• PhonePe received SEBI approval to proceed with its IPO and will file an updated DRHP.
• ReNew Energy announced plans to raise $500 million through a dollar-denominated bond issue.
• IndiGo shares recorded their biggest single-day gain in 16 months amid strong market sentiment.
• The RBI tightened Priority Sector Lending norms, mandating auditor certification for lenders.
• The Indian rupee weakened against the US dollar due to delays in trade agreement discussions.

                                              
Eg:
PhonePe Gets SEBI nod for IPO; company to file updated DRHP soon
ReNew lines up $500-million dollar bond issue
IndiGo posts biggest single-day gain in 16 months
RBI tightens PSL norms, mandates auditor certification for lenders
Rupee slips amid trade deal delay                                                                                         
Articles:
{articles}
""")

# ------------------------------
# Helpers
# ------------------------------
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


# ------------------------------
# Stock Price
# ------------------------------
def get_stock_price() -> str:
    if not os.path.exists(CSV_PATH):
        return "CSV not found"

    df = pd.read_csv(CSV_PATH)
    df["NAME OF COMPANY"] = df["NAME OF COMPANY"].str.lower()

    match = df[df["NAME OF COMPANY"].str.contains(STOCK.lower(), na=False)]
    if match.empty:
        return "Stock not found"

    symbol = f"{match.iloc[0]['SYMBOL']}.NS"

    try:
        res = requests.get(
            "https://api.api-ninjas.com/v1/stockprice",
            headers={"X-Api-Key": STOCK_API_KEY},
            params={"ticker": symbol},
            timeout=10
        )
        if res.status_code != 200:
            return "Stock price unavailable"

        return f"{symbol}: ₹ {res.json().get('price', 'N/A')}"
    except Exception:
        return "Stock price fetch failed"


# ------------------------------
# Fetch NewsAPI
# ------------------------------
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
            logger.warning(f"NewsAPI error for '{q}': {e}")

    logger.info(f"Fetched {len(articles)} NewsAPI articles")
    return articles[:MAX_NEWSAPI]


# ------------------------------
# Fetch RSS (Mandatory)
# ------------------------------
def fetch_rss_articles() -> List[Dict]:
    logger.info("Fetching Finance RSS feed")
    feed = feedparser.parse(FINANCE_RSS_FEED)

    articles = []
    for entry in feed.entries[:MAX_RSS]:
        articles.append(normalize_article({
            "title": entry.get("title"),
            "summary": entry.get("summary"),
            "link": entry.get("link"),
            "published": entry.get("published")
        }, "rss"))

    logger.info(f"Fetched {len(articles)} RSS articles")
    return articles


# ------------------------------
# Summarization
# ------------------------------
def summarize_articles(articles: List[Dict]) -> str:
    text = "\n".join(
        f"{idx+1}. {a['title']}"
        for idx, a in enumerate(articles)
    )

    try:
        res = llm.invoke(SUMMARY_PROMPT.format(
            SECTOR=SECTOR,
            STOCK=STOCK,
            articles=text
        ))
        return res.content.strip()
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return "Summary unavailable"


# ------------------------------
# Main Agent
# ------------------------------
def run_finance_agent() -> Dict:
    logger.info("Finance agent started")

    llm_raw = llm.invoke(QUERY_PROMPT.format(
        SECTOR=SECTOR,
        STOCK=STOCK
    )).content

    match = re.search(r"\[.*\]", llm_raw, re.DOTALL)
    queries = json.loads(match.group()) if match else [f"{STOCK} stock news"]

    newsapi_articles = fetch_newsapi_articles(queries)
    rss_articles = fetch_rss_articles()

    # Combine + dedupe
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

    final_articles = articles[:FINAL_ARTICLES]
    logger.info(f"Final selected finance articles: {len(final_articles)}")

    if not final_articles:
        return {}

    return {
        "title": "💰 Finance News",
        "stock_info": get_stock_price(),
        "summary": summarize_articles(final_articles),
        "articles": final_articles
    }
