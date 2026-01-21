# ------------------------------------------------------
# GLOBAL CONFIGURATION
# ------------------------------------------------------

# App
APP_NAME = "Agentic News Digest"
TIMEZONE = "Asia/Kolkata"

# Scheduler
DIGEST_INTERVAL_MINUTES = 10

# News
HOURS_BACK = 24
MIN_ARTICLES_PER_AGENT = 1
MAX_RETRIES = 3

# LLM
LLM_MODEL = "llama3.1:8b"
LLM_TEMPERATURE = 0
MAX_LLM_WORKERS = 5

# Agents
SPORTS_KEYWORDS = ["sports", "match", "tournament"]
TECH_KEYWORDS = ["technology", "ai", "software"]
FINANCE_KEYWORDS = ["stocks", "market", "finance"]

# Finance defaults
DEFAULT_FINANCE_SECTOR = "Technology"
DEFAULT_STOCK = "Infosys"

# Email
EMAIL_SUBJECT_PREFIX = "📰 Daily News Digest"
