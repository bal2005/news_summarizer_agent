# Personalized Multi-Domain News Summarizer

A Python-based project that fetches, filters, and summarizes the latest news across **Finance**, **Technology**, and **Sports** domains using **NewsAPI**, **RSS feeds**, and **LLM-based summarization** (via Ollama).  

The project provides a **Streamlit interface** where users can input the stock, sector, team, and technology topic to generate a personalized news summary.

---

## Features

- Fetches news from **NewsAPI** and **RSS feeds**.
- Deduplicates articles and prioritizes the most relevant ones.
- Filters articles using **LLM classification** to ensure domain relevance.
- Generates concise **bullet-point summaries** for each domain.
- Supports **dynamic input**:
  - Finance: Stock, Sector
  - Tech: Technology topic
  - Sports: Team, Sport
- Streamlit interface for **easy interaction**.

---

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/bal2005/news_summarizer_agent.git
cd news_summarizer
```
2. **Create Venv**

```bash
# Using conda
conda create -n newsenv python=3.11 -y
conda activate newsenv

# Or using venv
python -m venv newsenv
source newsenv/bin/activate  # Linux/macOS
newsenv\Scripts\activate     # Windows

```

3. ** Install Dependencies**
```
pip install -r requirements.txt
```

4.Add environment variables(.env)
```
NEWS_API_KEY=<your_newsapi_key>
STOCK_API_KEY=<your_stock_api_key>
```

## Agent Architecture

### Finance Agent
- Fetches stock and sector news from NewsAPI.
- Combines with RSS feeds if available.
- Returns top 5 articles with a concise summary.


### Tech Agent
- Fetches tech news from NewsAPI and RSS feed (Wired).
- Classifies relevance using LLM.
- Summarizes top 5 articles in bullet points.

### Sports Agent
- Fetches team/sport news from NewsAPI and RSS feeds (ESPN, Goal.com).
- Classifies relevance using LLM.
- Summarizes top 5 articles in bullet points.

## Configuration
- **MAX_NEWSAPI**: Maximum articles fetched from NewsAPI (default: 10)
- **MAX_RSS**: Maximum articles fetched from RSS feeds (default: 10)
- **FINAL_ARTICLES**: Number of articles summarized per domain (default: 5)

## Dependencies
- Python = 3.9
- [Streamlit](https://streamlit.io/)
- [newsapi-python](https://pypi.org/project/newsapi-python/)
- [feedparser](https://pypi.org/project/feedparser/)
- [pandas](https://pypi.org/project/pandas/)
- [langchain](https://www.langchain.com/)
- [langchain-ollama](https://pypi.org/project/langchain-ollama/)
- [requests](https://pypi.org/project/requests/)


## License
MIT License © [M Balasubramanian]


