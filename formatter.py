import discord
from datetime import datetime
from typing import List, Optional
import asyncio
import random

from news_fetcher import NewsArticle
from translator import Translator


# Cores por categoria
COLOR_AI = 0x5865F2
COLOR_VIBE = 0x57F287
COLOR_HEADER = 0xFEE75C
COLOR_ERROR = 0xED4245

# ── Frases de abertura do post diário (rotaciona aleatoriamente) ──────────────
DAILY_OPENERS = [
    "Bora ver o que tá rolando no mundo das máquinas pensantes 🤖",
    "A IA não tirou o final de semana e você também não vai tirar 😅",
    "Enquanto você dormia, a inteligência artificial não dormiu. Surpresa!",
    "Notícias fresquinhas do caos organizado que é o mundo da IA 🔥",
    "Hoje tem update e não é do seu sistema operacional (ou talvez seja, quem sabe 🙃)",
    "O futuro chegou mais cedo que o previsto. De novo. Como sempre.",
    "Separei as paradas mais importantes do dia pra você não precisar ficar no doomscroll ✌️",
    "Outro dia, outra revolução tecnológica. Relaxa que eu já filtrei o que importa 👇",
]

# ── Comentários por tipo de notícia (baseado em palavras-chave no título) ─────
def _witty_comment(title: str, source: str) -> str:
    t = title.lower()
    s = source.lower()

    if any(w in t for w in ["acqui", "comprou", "acquisition", "merger"]):
        return random.choice([
            "💰 Mais uma empresa engolindo outra. O capitalismo tá com fome.",
            "🤝 Fusão ou aquisição? Nos dois casos, alguém vai pagar mais caro.",
            "💸 Dinheiro trocando de mão em modo acelerado como sempre.",
        ])
    if any(w in t for w in ["billion", "funding", "raises", "invest", "bilhão", "investimento"]):
        return random.choice([
            "🤑 Mais grana entrando no ecossistema de IA. A bolha continua inflando.",
            "💵 Alguém apostou uma fortuna nisso. Espero que saiba o que tá fazendo.",
            "📈 Investidores viram IA e abriram a carteira. Clássico.",
        ])
    if any(w in t for w in ["launch", "release", "announces", "new model", "lança", "novo modelo"]):
        return random.choice([
            "🚀 Saiu coisa nova! Bora ver se dessa vez realmente muda tudo™️",
            "✨ Mais um lançamento. O hype tá garantido, a entrega veremos.",
            "🎉 Chegou novidade! Já tô curioso pra saber o que vai acontecer na prática.",
        ])
    if any(w in t for w in ["ban", "regulation", "law", "regulat", "lei", "proibição"]):
        return random.choice([
            "⚖️ Os governos tentando correr atrás do prejuízo de sempre.",
            "🏛️ Regulação chegando. Vai ajudar? Complicar? Tudo ao mesmo tempo?",
            "📜 Lei nova no pedaço. A IA segue indiferente.",
        ])
    if any(w in t for w in ["openai", "chatgpt", "gpt"]):
        return random.choice([
            "🤖 A OpenAI em cena. Novidade ou polêmica? Talvez os dois.",
            "👀 A empresa mais observada do Vale do Silício se mexeu de novo.",
            "🧠 ChatGPT/OpenAI na mídia. Bora ver o que aprontaram agora.",
        ])
    if any(w in t for w in ["google", "gemini", "deepmind"]):
        return random.choice([
            "🔍 Google tentando mostrar que não ficou pra trás. Olha só.",
            "🌐 Big G se mexendo no tabuleiro da IA. Interessante.",
        ])
    if any(w in t for w in ["anthropic", "claude"]):
        return random.choice([
            "🎭 A Anthropic sendo a Anthropic. Segurança e mais segurança.",
            "🧪 Claude apareceu. Vou fingir que não sou suspeito pra comentar isso.",
        ])
    if any(w in t for w in ["reddit", "r/"]) or "reddit" in s:
        return random.choice([
            "🔴 O Reddit falou. É relevante? O upvote dirá.",
            "📢 Voz das ruas (digitais): o Reddit pesou o dedo.",
            "🗳️ Comunidade deu seu veredito. Confira abaixo.",
        ])
    if any(w in t for w in ["vibecod", "cursor", "copilot", "vibe"]):
        return random.choice([
            "💻 Vibecoding em ação! Onde o prompt vira produto.",
            "⚡ A galera que programa com IA tá sempre arrumando algo novo.",
            "🎯 Mais um update no universo do código gerado por IA.",
        ])

    return random.choice([
        "👇 Deixa eu te contar o que aconteceu aqui.",
        "📌 Isso aqui vale a sua atenção.",
        "🔎 Achei relevante demais pra não compartilhar.",
        "🗞️ Saiu do forno. Clica e vai por dentro.",
        "💡 Mais um pedaço do puzzle que é o mundo da IA.",
    ])


def _source_emoji(source: str) -> str:
    s = source.lower()
    if "reddit" in s:        return "🔴"
    if "x @" in s or "twitter" in s: return "🐦"
    if "instagram" in s:     return "📸"
    if "techcrunch" in s:    return "🟢"
    if "wired" in s:         return "⚡"
    if "verge" in s:         return "🔷"
    if "ars" in s:           return "🔬"
    if "venturebeat" in s:   return "💰"
    if "mit" in s or "technology review" in s: return "🎓"
    return "📰"


def _format_date(date_str: Optional[str]) -> str:
    if not date_str:
        return "data misteriosa 🕵️"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return date_str


class NewsFormatter:

    async def build_article_embed(
        self,
        article: NewsArticle,
        color: int,
        translator: Translator,
    ) -> discord.Embed:
        title_pt = await translator.translate_title(article.title)
        desc_pt = ""
        if article.description:
            desc_pt = await translator.translate_description(article.description)

        source_emoji = _source_emoji(article.source)
        comment = _witty_comment(title_pt, article.source)

        embed = discord.Embed(
            title=f"{source_emoji} {title_pt}",
            url=article.url,
            description=f"*{comment}*\n\n{desc_pt[:300]}{'...' if len(desc_pt) > 300 else ''}",
            color=color,
        )

        embed.add_field(name="📍 Fonte", value=article.source, inline=True)
        embed.add_field(name="🕐 Publicado", value=_format_date(article.published_at), inline=True)

        if article.image_url:
            embed.set_image(url=article.image_url)

        embed.set_footer(text="Traduzido automaticamente • Clique no título para a matéria completa")
        return embed

    async def send_news_section(
        self,
        channel: discord.TextChannel,
        section_title: str,
        articles: List[NewsArticle],
        translator: Translator,
        color: int = COLOR_AI,
    ):
        if not articles:
            embed = discord.Embed(
                title=section_title,
                description="Nada relevante encontrado agora. Calma, o mundo não parou — só tá em modo de espera.",
                color=COLOR_ERROR,
            )
            await channel.send(embed=embed)
            return

        total = len(articles)
        header = discord.Embed(
            title=section_title,
            description=f"**{total} destaques** selecionados hoje — cada um em sua própria mensagem abaixo 👇",
            color=COLOR_HEADER,
        )
        await channel.send(embed=header)
        await asyncio.sleep(1.0)

        for i, article in enumerate(articles, start=1):
            try:
                embed = await self.build_article_embed(article, color, translator)
                embed.set_author(name=f"Notícia {i} de {total}")
                await channel.send(embed=embed)
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"[Formatter] Erro ao enviar artigo: {e}")

        await channel.send(f"```\n{'─' * 40}\n```")
        await asyncio.sleep(1.0)

    async def send_daily_header(self, channel: discord.TextChannel, notify: bool = False):
        """
        notify=True: inclui @here para push notification no mobile (só no post automático das 17h)
        """
        now = datetime.utcnow()
        opener = random.choice(DAILY_OPENERS)

        embed = discord.Embed(
            title=f"📡 IA Daily — {now.strftime('%d/%m/%Y')}",
            description=(
                f"{opener}\n\n"
                "Abaixo estão os **destaques de hoje** em **Inteligência Artificial** e **Vibecoding**, "
                "com tudo traduzido e mastigado pra você. Links originais estão no título de cada card."
            ),
            color=COLOR_AI,
        )
        embed.set_footer(text="Curadoria automática diária • 17h BRT")

        if notify:
            # @everyone garante push notification para TODOS os membros do servidor
            try:
                await channel.send("@everyone", embed=embed)
            except Exception:
                await channel.send(embed=embed)
        else:
            await channel.send(embed=embed)
