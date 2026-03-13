"""
Scraper para Instagram via instaloader.
Funciona com qualquer conta Instagram gratuita.
Requer: pip install instaloader
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

from news_fetcher import NewsArticle


# Perfis de IA e tecnologia para monitorar
AI_PROFILES = [
    "openai",
    "googleai",
    "metaai",
    "anthropic_ai",
    "hugging_face",
    "nvidia_ai",
    "artificialintelligencedaily",
    "ai.trends",
    "deeplearning.ai",
    "theaipaper",
]

VIBE_PROFILES = [
    "cursor.so",
    "github",
    "codewithme.ai",
]

# Hashtags para buscar (instaloader suporta busca por hashtag)
AI_HASHTAGS = [
    "inteligenciaartificial",
    "artificialintelligence",
    "machinelearning",
    "aitools",
    "generativeai",
    "llm",
]

VIBE_HASHTAGS = [
    "vibecoding",
    "vibecoder",
    "aicoding",
    "codewithAI",
]


class InstagramScraper:
    def __init__(self):
        self.loader = None
        self._initialized = False

    def _init(self):
        if self._initialized:
            return

        ig_user = os.getenv("INSTAGRAM_USERNAME")
        ig_pass = os.getenv("INSTAGRAM_PASSWORD")

        if not ig_user or not ig_pass:
            print("[Instagram] INSTAGRAM_USERNAME ou INSTAGRAM_PASSWORD não configurados — scraper desativado.")
            return

        try:
            import instaloader
            self.loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                quiet=True,
            )

            # Sessão persistente para não logar toda vez
            session_file = Path(f"ig_session_{ig_user}")
            if session_file.exists():
                try:
                    self.loader.load_session_from_file(ig_user, str(session_file))
                    print("[Instagram] Sessão carregada do cache.")
                    self._initialized = True
                    return
                except Exception:
                    pass

            # Login
            self.loader.login(ig_user, ig_pass)
            self.loader.save_session_to_file(str(session_file))
            self._initialized = True
            print("[Instagram] Login realizado com sucesso.")

        except ImportError:
            print("[Instagram] instaloader não instalado. Rode: pip install instaloader")
        except Exception as e:
            print(f"[Instagram] Erro ao inicializar: {e}")

    def _post_to_article(self, post) -> Optional[NewsArticle]:
        try:
            import instaloader
            caption = post.caption or ""
            if len(caption) < 30:
                return None

            title = caption[:120].replace("\n", " ")
            title += "..." if len(caption) > 120 else ""

            image_url = None
            try:
                image_url = post.url  # URL da imagem/thumbnail
            except Exception:
                pass

            return NewsArticle(
                title=title,
                url=f"https://www.instagram.com/p/{post.shortcode}/",
                description=caption[:400],
                image_url=image_url,
                source=f"Instagram @{post.owner_username}",
                published_at=post.date_utc.isoformat() if post.date_utc else None,
                author=f"@{post.owner_username}",
            )
        except Exception as e:
            print(f"[Instagram] Erro ao converter post: {e}")
            return None

    def _fetch_from_profile(self, username: str, max_posts: int, cutoff: datetime) -> List[NewsArticle]:
        articles = []
        try:
            import instaloader
            profile = instaloader.Profile.from_username(self.loader.context, username)
            for post in profile.get_posts():
                if post.date_utc < cutoff:
                    break
                article = self._post_to_article(post)
                if article:
                    articles.append(article)
                if len(articles) >= max_posts:
                    break
        except Exception as e:
            print(f"[Instagram] Erro ao buscar @{username}: {e}")
        return articles

    def _fetch_from_hashtag(self, hashtag: str, max_posts: int, cutoff: datetime) -> List[NewsArticle]:
        articles = []
        try:
            import instaloader
            tag = instaloader.Hashtag.from_name(self.loader.context, hashtag)
            for post in tag.get_top_posts():
                if post.date_utc and post.date_utc < cutoff:
                    continue
                article = self._post_to_article(post)
                if article:
                    articles.append(article)
                if len(articles) >= max_posts:
                    break
        except Exception as e:
            print(f"[Instagram] Erro ao buscar #{hashtag}: {e}")
        return articles

    async def get_ai_posts(self, max_results: int = 6) -> List[NewsArticle]:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init)

        if not self.loader or not self._initialized:
            return []

        cutoff = datetime.utcnow() - timedelta(hours=24)
        all_articles: List[NewsArticle] = []

        # Busca em perfis conhecidos
        for profile in AI_PROFILES[:5]:
            results = await loop.run_in_executor(
                None, lambda p=profile: self._fetch_from_profile(p, 2, cutoff)
            )
            all_articles.extend(results)
            await asyncio.sleep(1.5)  # Pausa para não ser bloqueado

        # Complementa com hashtags se precisar
        if len(all_articles) < max_results:
            for hashtag in AI_HASHTAGS[:3]:
                results = await loop.run_in_executor(
                    None, lambda h=hashtag: self._fetch_from_hashtag(h, 3, cutoff)
                )
                all_articles.extend(results)
                await asyncio.sleep(1.5)

        # Deduplica por shortcode/URL
        seen = set()
        unique = []
        for art in all_articles:
            if art.url not in seen:
                seen.add(art.url)
                unique.append(art)

        return unique[:max_results]

    async def get_vibe_posts(self, max_results: int = 4) -> List[NewsArticle]:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init)

        if not self.loader or not self._initialized:
            return []

        cutoff = datetime.utcnow() - timedelta(hours=24)
        all_articles: List[NewsArticle] = []

        for profile in VIBE_PROFILES:
            results = await loop.run_in_executor(
                None, lambda p=profile: self._fetch_from_profile(p, 2, cutoff)
            )
            all_articles.extend(results)
            await asyncio.sleep(1.5)

        for hashtag in VIBE_HASHTAGS:
            results = await loop.run_in_executor(
                None, lambda h=hashtag: self._fetch_from_hashtag(h, 3, cutoff)
            )
            all_articles.extend(results)
            await asyncio.sleep(1.5)

        seen = set()
        unique = []
        for art in all_articles:
            if art.url not in seen:
                seen.add(art.url)
                unique.append(art)

        return unique[:max_results]
