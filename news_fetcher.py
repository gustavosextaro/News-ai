import asyncio
import aiohttp
import feedparser
import requests
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from typing import List, Optional
import re

# Session requests com User-Agent de browser para evitar bloqueios
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
})

import config


class NewsArticle:
    def __init__(
        self,
        title: str,
        url: str,
        description: str = "",
        image_url: Optional[str] = None,
        source: str = "",
        published_at: Optional[str] = None,
        author: Optional[str] = None,
    ):
        self.title = title
        self.url = url
        self.description = description
        self.image_url = image_url
        self.source = source
        self.published_at = published_at
        self.author = author

    def __repr__(self):
        return f"<NewsArticle title='{self.title[:40]}...' source='{self.source}'>"


class NewsFetcher:
    def __init__(self):
        self.newsapi = None
        self._setup_clients()

    def _setup_clients(self):
        if config.NEWSAPI_KEY:
            try:
                self.newsapi = NewsApiClient(api_key=config.NEWSAPI_KEY)
            except Exception as e:
                print(f"[NewsAPI] Erro ao inicializar: {e}")

    # ── NewsAPI ──────────────────────────────────────────────────────────────

    def _fetch_newsapi(self, query: str, max_results: int = 10) -> List[NewsArticle]:
        if not self.newsapi:
            return []
        try:
            response = self.newsapi.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                page_size=max_results,
            )
            articles = []
            for item in response.get("articles", []):
                articles.append(
                    NewsArticle(
                        title=item.get("title", "Sem título"),
                        url=item.get("url", ""),
                        description=item.get("description") or item.get("content") or "",
                        image_url=item.get("urlToImage"),
                        source=item.get("source", {}).get("name", "NewsAPI"),
                        published_at=item.get("publishedAt"),
                        author=item.get("author"),
                    )
                )
            return articles
        except Exception as e:
            print(f"[NewsAPI] Erro ao buscar '{query}': {e}")
            return []

    # ── Reddit via RSS público (sem API, sem conta) ───────────────────────────

    def _fetch_reddit_rss(self, subreddits: List[str], max_results: int = 10) -> List[NewsArticle]:
        """
        Usa os RSS feeds nativos do Reddit — totalmente gratuito, sem autenticação.
        URL: https://www.reddit.com/r/SUBREDDIT/hot.rss
        Usa requests com User-Agent de browser para evitar bloqueio 403.
        """
        articles = []
        cutoff = datetime.utcnow() - timedelta(hours=24)

        for subreddit in subreddits:
            feed_url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=10"
            try:
                resp = _session.get(feed_url, timeout=10)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                for entry in feed.entries:
                    pub = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            pub = datetime(*entry.published_parsed[:6])
                            if pub < cutoff:
                                continue
                        except Exception:
                            pass

                    title = entry.get("title", "")
                    summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))
                    url = entry.get("link", "")

                    # Extrai thumbnail do HTML do summary
                    image_url = None
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get("summary", ""))
                    if img_match:
                        img_candidate = img_match.group(1)
                        # Filtra ícones pequenos do Reddit
                        if "icon" not in img_candidate and "emoji" not in img_candidate:
                            image_url = img_candidate

                    articles.append(
                        NewsArticle(
                            title=title,
                            url=url,
                            description=summary[:300],
                            image_url=image_url,
                            source=f"Reddit r/{subreddit}",
                            published_at=pub.isoformat() if pub else None,
                        )
                    )

                    if len(articles) >= max_results:
                        return articles

            except Exception as e:
                print(f"[Reddit RSS] Erro ao buscar r/{subreddit}: {e}")

        return articles

    # ── RSS Feeds de sites de notícias ────────────────────────────────────────

    def _fetch_rss(self, feeds: List[str], keywords: List[str], max_results: int = 10) -> List[NewsArticle]:
        articles = []
        keywords_lower = [k.lower() for k in keywords]
        cutoff = datetime.utcnow() - timedelta(hours=24)

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    combined_text = (title + " " + summary).lower()

                    if not any(kw in combined_text for kw in keywords_lower):
                        continue

                    pub = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            pub = datetime(*entry.published_parsed[:6])
                            if pub < cutoff:
                                continue
                        except Exception:
                            pass

                    image_url = None
                    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                        image_url = entry.media_thumbnail[0].get("url")
                    elif hasattr(entry, "media_content") and entry.media_content:
                        image_url = entry.media_content[0].get("url")

                    articles.append(
                        NewsArticle(
                            title=title,
                            url=entry.get("link", ""),
                            description=re.sub(r"<[^>]+>", "", summary)[:300],
                            image_url=image_url,
                            source=feed.feed.get("title", feed_url),
                            published_at=pub.isoformat() if pub else None,
                        )
                    )

                    if len(articles) >= max_results:
                        return articles
            except Exception as e:
                print(f"[RSS] Erro ao buscar {feed_url}: {e}")

        return articles

    # ── Relevance scoring ────────────────────────────────────────────────────

    def _score(self, article: NewsArticle) -> int:
        score = 0
        text = (article.title + " " + article.description).lower()

        # Eventos de alto impacto
        high_impact = ["launch", "release", "raises", "billion", "acqui", "announce",
                       "breakthrough", "ban", "regulation", "lança", "bilhão", "investe"]
        for kw in high_impact:
            if kw in text:
                score += 3

        # Empresas/nomes de grande repercussão
        big_names = ["openai", "chatgpt", "google", "anthropic", "meta", "microsoft",
                     "nvidia", "gemini", "claude", "gpt", "llm", "deepmind", "cursor"]
        for kw in big_names:
            if kw in text:
                score += 2

        # Fontes mais confiáveis
        authoritative = ["techcrunch", "verge", "wired", "venturebeat", "mit", "ars technica",
                         "x @openai", "x @anthropic", "x @googledeep"]
        for src in authoritative:
            if src in article.source.lower():
                score += 2

        # Tem imagem (mais engajamento visual)
        if article.image_url:
            score += 1

        return score

    def _rank_by_relevance(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        return sorted(articles, key=self._score, reverse=True)

    # ── Deduplication ────────────────────────────────────────────────────────

    @staticmethod
    def _title_words(title: str) -> set:
        """Normaliza título em set de palavras, removendo stopwords curtas."""
        stop = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "is",
                "are", "was", "and", "or", "with", "its", "it", "as", "by",
                "de", "do", "da", "em", "no", "na", "um", "uma", "os", "as"}
        words = re.sub(r"[^a-z0-9 ]", "", title.lower()).split()
        return {w for w in words if len(w) > 2 and w not in stop}

    def _is_duplicate(self, title: str, seen_word_sets: list) -> bool:
        """Retorna True se o título é similar demais a algum já visto (Jaccard >= 0.55)."""
        words = self._title_words(title)
        if not words:
            return False
        for seen in seen_word_sets:
            if not seen:
                continue
            intersection = words & seen
            union = words | seen
            if len(union) > 0 and len(intersection) / len(union) >= 0.55:
                return True
        return False

    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        seen_urls = set()
        seen_word_sets = []
        unique = []
        for art in articles:
            url_key = art.url.split("?")[0].rstrip("/")
            if url_key in seen_urls:
                continue
            if self._is_duplicate(art.title, seen_word_sets):
                continue
            seen_urls.add(url_key)
            seen_word_sets.append(self._title_words(art.title))
            unique.append(art)
        return unique

    # ── Public methods ───────────────────────────────────────────────────────

    async def get_ai_news(self) -> List[NewsArticle]:
        loop = asyncio.get_event_loop()
        all_articles: List[NewsArticle] = []

        # NewsAPI
        for term in config.AI_SEARCH_TERMS[:4]:
            results = await loop.run_in_executor(
                None, lambda t=term: self._fetch_newsapi(t, max_results=5)
            )
            all_articles.extend(results)

        # Reddit via RSS público (sem API)
        reddit_results = await loop.run_in_executor(
            None, lambda: self._fetch_reddit_rss(config.AI_SUBREDDITS, max_results=10)
        )
        all_articles.extend(reddit_results)

        # RSS de sites de notícias
        rss_results = await loop.run_in_executor(
            None,
            lambda: self._fetch_rss(
                config.RSS_FEEDS,
                keywords=["artificial intelligence", "AI", "machine learning", "LLM", "ChatGPT", "inteligência artificial"],
                max_results=10,
            ),
        )
        all_articles.extend(rss_results)

        # X (Twitter) via Nitter RSS
        try:
            from x_scraper import XScraper
            x = XScraper()
            x_results = await x.get_ai_tweets(max_results=6)
            all_articles.extend(x_results)
        except Exception as e:
            print(f"[NewsFetcher] X scraper indisponível: {e}")

        # Instagram via instaloader
        try:
            from instagram_scraper import InstagramScraper
            ig = InstagramScraper()
            ig_results = await ig.get_ai_posts(max_results=4)
            all_articles.extend(ig_results)
        except Exception as e:
            print(f"[NewsFetcher] Instagram scraper indisponível: {e}")

        unique = self._deduplicate(all_articles)
        ranked = self._rank_by_relevance(unique)
        return ranked[: config.MAX_AI_NEWS]

    async def get_vibecoding_news(self) -> List[NewsArticle]:
        loop = asyncio.get_event_loop()
        all_articles: List[NewsArticle] = []

        # NewsAPI
        for term in config.VIBE_SEARCH_TERMS[:3]:
            results = await loop.run_in_executor(
                None, lambda t=term: self._fetch_newsapi(t, max_results=5)
            )
            all_articles.extend(results)

        # Reddit via RSS público (sem API)
        reddit_results = await loop.run_in_executor(
            None, lambda: self._fetch_reddit_rss(config.VIBE_SUBREDDITS, max_results=10)
        )
        all_articles.extend(reddit_results)

        # X (Twitter) via Nitter RSS
        try:
            from x_scraper import XScraper
            x = XScraper()
            x_results = await x.get_vibe_tweets(max_results=5)
            all_articles.extend(x_results)
        except Exception as e:
            print(f"[NewsFetcher] X scraper (vibe) indisponível: {e}")

        # Instagram via instaloader
        try:
            from instagram_scraper import InstagramScraper
            ig = InstagramScraper()
            ig_results = await ig.get_vibe_posts(max_results=3)
            all_articles.extend(ig_results)
        except Exception as e:
            print(f"[NewsFetcher] Instagram scraper (vibe) indisponível: {e}")

        # RSS de sites de notícias
        rss_results = await loop.run_in_executor(
            None,
            lambda: self._fetch_rss(
                config.RSS_FEEDS,
                keywords=["vibecoding", "vibe coding", "AI coding", "code with AI", "cursor", "copilot"],
                max_results=5,
            ),
        )
        all_articles.extend(rss_results)

        unique = self._deduplicate(all_articles)
        ranked = self._rank_by_relevance(unique)
        return ranked[: config.MAX_VIBE_NEWS]
