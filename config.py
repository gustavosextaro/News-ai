import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NEWS_CHANNEL_ID = int(os.getenv("NEWS_CHANNEL_ID", "0"))

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
RESET_HOUR = int(os.getenv("RESET_HOUR", "17"))
RESET_MINUTE = int(os.getenv("RESET_MINUTE", "0"))

MAX_AI_NEWS = int(os.getenv("MAX_AI_NEWS", "8"))
MAX_VIBE_NEWS = int(os.getenv("MAX_VIBE_NEWS", "5"))

# Termos de busca para IA
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "machine learning",
    "ChatGPT",
    "OpenAI",
    "Google Gemini",
    "Anthropic Claude",
    "AI startup",
    "LLM",
    "generative AI",
    "inteligência artificial",
]

# Termos de busca para Vibecoding
VIBE_SEARCH_TERMS = [
    "vibecoding",
    "vibe coding",
    "AI coding",
    "cursor IDE",
    "copilot coding",
    "AI programmer",
    "code with AI",
]

# Subreddits relevantes
AI_SUBREDDITS = ["artificial", "MachineLearning", "ChatGPT", "singularity", "OpenAI", "technology"]
VIBE_SUBREDDITS = ["vibecoding", "ChatGPTCoding", "AIAssisted", "cursor_ai", "learnprogramming"]

# RSS feeds de tecnologia/IA
RSS_FEEDS = [
    "https://feeds.feedburner.com/TechCrunch",
    "https://www.technologyreview.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/category/ai/latest/rss",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
]
