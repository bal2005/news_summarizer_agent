# agents/tech_agent.py

import os
import json
import re
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
from dotenv import load_dotenv
from newsapi import NewsApiClient
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate

# ------------------------------------------------------
# Logging setup
# ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("TECH_AGENT")

# ------------------------------------------------------
# Environment
# ------------------------------------------------------
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ------------------------------------------------------
# Clients
# ------------------------------------------------------
newsapi = NewsApiClient(api_key=NEWS_API_KEY)
llm = ChatOllama(model="llama3.1:8b", temperature=0)

# ------------------------------------------------------
# Constants
# ------------------------------------------------------
TECH = "Artificial Intelligence"

MAX_LLM_WORKERS = 5

MAX_NEWSAPI = 10
MAX_RSS = 10
FINAL_ARTICLES = 5

TECH_RSS_FEED = "https://www.wired.com/feed/rss"

# ------------------------------------------------------
# Prompts
# ------------------------------------------------------
QUERY_PROMPT = PromptTemplate.from_template("""
Generate 5 short search queries for recent technology news.

Rules:
- No boolean operators
- Simple human phrases
- Focus only on technology: {TECH}
- 2–3 words each
Return ONLY a JSON array of strings.
""")

CLASSIFY_PROMPT = PromptTemplate.from_template("""
Is this article about {TECH}?
YES or NO only.

Title: {title}
Description: {description}
""")

SUMMARY_PROMPT = PromptTemplate.from_template("""
Summarize the following {TECH} news.

Rules:
- EXACTLY one bullet per article
- 3–5 bullets total
- Each bullet must describe a DIFFERENT news event
- No intro or meta text
- Focus on real updates (products, research, regulation, companies)
                                              
Eg:
Summary:
• A new study warned that rising AI-driven data center demand could significantly increase US carbon emissions over the next decade.
• Researchers proposed greater use of renewable energy to offset emissions from expanding data centers.
• Anthropic’s president stated that the concept of Artificial General Intelligence may already be outdated.
• Elon Musk predicted China will surpass other nations in AI compute capacity.
• The World Economic Forum outlined four AI-driven job market scenarios for 2030.

The AI Boom Will Increase US Carbon Emissions—but It Doesn’t Have To
Anthropic president questions relevance of AGI concept
Elon Musk says China will dominate AI compute
WEF outlines AI-driven futures for jobs by 2030
Data centers drive rising power demand

Articles:
{articles}
""")

# ------------------------------------------------------
# Helpers
# ------------------------------------------------------
def generate_queries() -> List[str]:
    logger.info("Generating Tech queries via LLM")
    try:
        res = llm.invoke(QUERY_PROMPT.format(TECH=TECH))
        match = re.search(r"\[.*\]", res.content, re.DOTALL)
        if match:
            queries = json.loads(match.group())
            if isinstance(queries, list) and queries:
                return queries
    except Exception as e:
        logger.warning(f"Query generation failed: {e}")

    return [f"{TECH} news"]

def fetch_newsapi_articles(queries: List[str]) -> List[Dict]:
    logger.info("Fetching Tech articles from NewsAPI")
    articles = []

    for q in queries:
        try:
            res = newsapi.get_everything(
                q=q,
                language="en",
                page_size=MAX_NEWSAPI
            )
            articles.extend(res.get("articles", []))
        except Exception as e:
            logger.error(f"NewsAPI error for query '{q}': {e}")

    logger.info(f"Fetched {len(articles)} NewsAPI articles")
    return articles[:MAX_NEWSAPI]

def fetch_rss_articles() -> List[Dict]:
    logger.info("Fetching Tech articles from RSS (Wired)")
    feed = feedparser.parse(TECH_RSS_FEED)

    articles = []
    for entry in feed.entries[:MAX_RSS]:
        articles.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "url": entry.get("link", "")
        })

    logger.info(f"Fetched {len(articles)} RSS articles")
    return articles

def deduplicate(articles: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for a in articles:
        url = a.get("url")
        if url and url not in seen:
            seen.add(url)
            unique.append(a)
    return unique

def classify_article(article: Dict) -> bool:
    try:
        res = llm.invoke(CLASSIFY_PROMPT.format(
            TECH=TECH,
            title=article.get("title", ""),
            description=article.get("summary", "")
        ))
        return res.content.strip().upper().startswith("YES")
    except Exception as e:
        logger.error(f"Classification error: {e}")
        return False

def summarize(articles: List[Dict]) -> str:
    compact = "\n".join(
        f"Title: {a.get('title')}\nContent: {a.get('summary')}\n"
        for a in articles
    )

    res = llm.invoke(SUMMARY_PROMPT.format(
        TECH=TECH,
        articles=compact
    ))
    return res.content.strip()

# ------------------------------------------------------
# AGENT ENTRY
# ------------------------------------------------------
def run_tech_agent() -> Dict:
    logger.info("💻 Running Tech Agent")

    # 1. Fetch from both sources
    rss_articles = fetch_rss_articles()
    queries = generate_queries()
    newsapi_articles = fetch_newsapi_articles(queries)

    # 2. Combine with fallback logic
    combined = deduplicate(rss_articles + newsapi_articles)

    if not combined:
        logger.warning("No Tech articles found from any source")
        return {}

    # 3. LLM classification (parallel)
    relevant = []
    with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:
        futures = {executor.submit(classify_article, a): a for a in combined}
        for f in as_completed(futures):
            if f.result():
                relevant.append(futures[f])

    if not relevant:
        logger.warning("No relevant Tech articles after classification")
        return {}

    # 4. Final selection
    final_articles = relevant[:FINAL_ARTICLES]
    logger.info(f"Selected {len(final_articles)} final Tech articles")

    # 5. Summarize
    summary = summarize(final_articles)

    logger.info("✅ Tech Agent completed")
    return {
        "title": "💻 Technology",
        "summary": summary,
        "articles": final_articles
    }
