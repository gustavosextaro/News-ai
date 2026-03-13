"""
Scraper para X (Twitter) via Nitter RSS.

Nitter é um frontend alternativo e open-source do X que expõe RSS feeds públicos.
- Não requer conta nem API paga
- Funciona com Python 3.9+
- Pega posts de contas e buscas por termo

Instâncias públicas: https://status.d420.de (lista de instâncias ativas)
Você pode rodar sua própria instância local com Docker (ver SETUP.md).
"""

import asyncio
import feedparser
import aiohttp
from datetime import datetime
from typing import List, Optional
import re

from news_fetcher import NewsArticle


# Instâncias Nitter públicas (testadas em ordem até achar uma que funcione)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.it",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
]

# Contas relevantes de IA para monitorar
AI_ACCOUNTS = [
    "OpenAI",
    "AnthropicAI",
    "GoogleDeepMind",
    "sama",           # Sam Altman
    "karpathy",       # Andrej Karpathy
    "ylecun",         # Yann LeCun
    "MistralAI",
    "huggingface",
    "xai",
    "AIatMeta",
]

VIBE_ACCOUNTS = [
    "cursor_ai",
    "simonw",         # Simon Willison
    "swyx",
    "levelsio",
    "aider_ai",
]

# Termos de busca (Nitter suporta busca via RSS)
AI_SEARCH_TERMS = [
    "artificial intelligence",
    "inteligência artificial",
    "LLM release",
    "AI startup",
    "ChatGPT",
]

VIBE_SEARCH_TERMS = [
    "vibecoding",
    "vibe coding",
    "built with cursor",
    "ai coding",
]


class XScraper:
    def __init__(self):
        self._working_instance: Optional[str] = None

    async def _find_working_instance(self) -> Optional[str]:
        """Testa as instâncias Nitter e retorna a primeira que funcionar."""
        if self._working_instance:
            return self._working_instance

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            for instance in NITTER_INSTANCES:
                try:
                    async with session.get(f"{instance}/OpenAI/rss") as resp:
                        if resp.status == 200:
                            self._working_instance = instance
                            print(f"[XScraper] Usando instância Nitter: {instance}")
                            return instance
                except Exception:
                    continue

        print("[XScraper] Nenhuma instância Nitter disponível no momento.")
        return None

    def _parse_nitter_feed(self, feed_url: str, max_items: int = 3) -> List[NewsArticle]:
        """
        Não filtra por data — o feed Nitter já vem ordenado por recência.
        Pega apenas os primeiros max_items para não sobrecarregar.
        """
        articles = []
        try:
            import requests as req_lib
            resp = req_lib.get(feed_url, timeout=8, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:max_items]:
                pub = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                title = entry.get("title", "")
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))
                url = entry.get("link", "")

                # Converte URL do Nitter para URL real do X
                x_url = re.sub(r"https?://[^/]+/", "https://x.com/", url)

                # Extrai imagem se houver
                image_url = None
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url")
                elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get("url")
                # Tenta extrair imagem do HTML do summary
                if not image_url:
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get("summary", ""))
                    if img_match:
                        image_url = img_match.group(1)

                # Extrai o nome da conta do feed
                author = feed.feed.get("title", "").replace(" / Nitter", "").strip()

                if len(summary) < 30:
                    continue

                articles.append(
                    NewsArticle(
                        title=summary[:120] + ("..." if len(summary) > 120 else ""),
                        url=x_url,
                        description=summary[:400],
                        image_url=image_url,
                        source=f"X {author}",
                        published_at=pub.isoformat() if pub else None,
                        author=author,
                    )
                )
        except Exception as e:
            print(f"[XScraper] Erro ao parsear feed {feed_url}: {e}")
        return articles

    async def _fetch_account(
        self, instance: str, account: str, max_items: int = 2
    ) -> List[NewsArticle]:
        feed_url = f"{instance}/{account}/rss"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._parse_nitter_feed(feed_url, max_items)
        )

    async def _fetch_search(
        self, instance: str, query: str, max_items: int = 4
    ) -> List[NewsArticle]:
        import urllib.parse
        encoded = urllib.parse.quote(query)
        feed_url = f"{instance}/search/rss?q={encoded}&f=tweets"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._parse_nitter_feed(feed_url, max_items)
        )

    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        seen = set()
        unique = []
        for art in articles:
            key = art.url.split("?")[0]
            if key not in seen:
                seen.add(key)
                unique.append(art)
        return unique

    async def get_ai_tweets(self, max_results: int = 8) -> List[NewsArticle]:
        instance = await self._find_working_instance()
        if not instance:
            return []

        all_articles: List[NewsArticle] = []

        # 2 tweets mais recentes de cada conta principal
        for account in AI_ACCOUNTS[:6]:
            try:
                results = await self._fetch_account(instance, account, max_items=2)
                all_articles.extend(results)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[XScraper] Erro ao buscar @{account}: {e}")

        # Busca por termos para complementar
        for term in AI_SEARCH_TERMS[:3]:
            try:
                results = await self._fetch_search(instance, term, max_items=3)
                all_articles.extend(results)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[XScraper] Erro na busca '{term}': {e}")

        return self._deduplicate(all_articles)[:max_results]

    async def get_vibe_tweets(self, max_results: int = 5) -> List[NewsArticle]:
        instance = await self._find_working_instance()
        if not instance:
            return []

        all_articles: List[NewsArticle] = []

        for account in VIBE_ACCOUNTS:
            try:
                results = await self._fetch_account(instance, account, max_items=2)
                all_articles.extend(results)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[XScraper] Erro ao buscar @{account}: {e}")

        for term in VIBE_SEARCH_TERMS:
            try:
                results = await self._fetch_search(instance, term, max_items=3)
                all_articles.extend(results)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[XScraper] Erro na busca vibecoding '{term}': {e}")

        return self._deduplicate(all_articles)[:max_results]
