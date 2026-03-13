import discord
from discord.ext import commands, tasks
from datetime import time, datetime
import asyncio
import pytz
import sys

import config
from news_fetcher import NewsFetcher
from translator import Translator
from formatter import NewsFormatter, COLOR_AI, COLOR_VIBE

# ── Validação da configuração ─────────────────────────────────────────────────

def validate_config():
    errors = []
    if not config.DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN não configurado no .env")
    if not config.NEWS_CHANNEL_ID:
        errors.append("NEWS_CHANNEL_ID não configurado no .env")
    if not config.NEWSAPI_KEY:
        print("[AVISO] NEWSAPI_KEY não configurado — notícias do NewsAPI desativadas.")
    if errors:
        for err in errors:
            print(f"[ERRO] {err}")
        sys.exit(1)

validate_config()

# ── Bot setup ─────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
fetcher = NewsFetcher()
translator = Translator(target_lang="pt")
formatter = NewsFormatter()

tz = pytz.timezone(config.TIMEZONE)
reset_time = time(hour=config.RESET_HOUR, minute=config.RESET_MINUTE, tzinfo=tz)


# ── Segurança: restringe comandos a administradores ───────────────────────────

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)


async def _silent_delete(ctx):
    """Apaga a mensagem de comando para não expor comandos no canal."""
    try:
        await ctx.message.delete()
    except Exception:
        pass


# ── Task agendada ─────────────────────────────────────────────────────────────

@tasks.loop(time=reset_time)
async def daily_news():
    channel = bot.get_channel(config.NEWS_CHANNEL_ID)
    if not channel:
        print(f"[Bot] Canal {config.NEWS_CHANNEL_ID} não encontrado.")
        return
    # notify=True envia @here → push notification no mobile de todos os membros
    await _post_all_news(channel, notify=True)


@daily_news.before_loop
async def before_daily_news():
    await bot.wait_until_ready()
    print(f"[Bot] Task agendada. Próximo post: {daily_news.next_iteration}")


# ── Função central de postagem ────────────────────────────────────────────────

async def _post_all_news(channel: discord.TextChannel, notify: bool = False):
    print(f"[Bot] Buscando notícias ({datetime.now(tz).strftime('%d/%m/%Y %H:%M')})")

    await formatter.send_daily_header(channel, notify=notify)

    ai_task = asyncio.create_task(fetcher.get_ai_news())
    vibe_task = asyncio.create_task(fetcher.get_vibecoding_news())
    ai_news, vibe_news = await asyncio.gather(ai_task, vibe_task)

    print(f"[Bot] {len(ai_news)} IA | {len(vibe_news)} Vibecoding")

    await formatter.send_news_section(
        channel,
        "🧠 Inteligência Artificial — Destaques do Dia",
        ai_news,
        translator,
        color=COLOR_AI,
    )

    await formatter.send_news_section(
        channel,
        "💻 Vibecoding — Quem Tá Construindo com IA",
        vibe_news,
        translator,
        color=COLOR_VIBE,
    )

    print("[Bot] Notícias postadas.")


# ── Eventos ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"[Bot] Conectado como {bot.user} (ID: {bot.user.id})")
    print(f"[Bot] Reset diário: {config.RESET_HOUR:02d}:{config.RESET_MINUTE:02d} ({config.TIMEZONE})")
    print(f"[Bot] Canal: {config.NEWS_CHANNEL_ID}")
    daily_news.start()


@bot.event
async def on_command_error(ctx, error):
    """Engole erros de permissão silenciosamente — usuários normais não veem nada."""
    if isinstance(error, commands.CheckFailure):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        return
    # Outros erros: loga no terminal
    print(f"[Bot] Erro no comando '{ctx.command}': {error}")


# ── Comandos (somente administradores) ───────────────────────────────────────

@bot.command(name="noticias", aliases=["news", "notícias"])
@is_admin()
async def fetch_news_now(ctx):
    """[ADMIN] Força busca e postagem imediata das notícias."""
    await _silent_delete(ctx)
    msg = await ctx.channel.send("🔍 Buscando as últimas notícias...")
    try:
        await _post_all_news(ctx.channel, notify=False)
        await msg.delete()
    except Exception as e:
        await msg.edit(content=f"❌ Erro: {e}")


@bot.command(name="proxima", aliases=["next"])
@is_admin()
async def next_update(ctx):
    """[ADMIN] Mostra quando será a próxima atualização."""
    await _silent_delete(ctx)
    next_run = daily_news.next_iteration
    if next_run:
        next_run_local = next_run.astimezone(tz)
        embed = discord.Embed(
            description=f"⏰ Próximo post: **{next_run_local.strftime('%d/%m/%Y às %H:%M')}**",
            color=0x5865F2,
        )
    else:
        embed = discord.Embed(description="⚠️ Agendador não iniciado.", color=0xED4245)
    msg = await ctx.channel.send(embed=embed)
    await asyncio.sleep(8)
    await msg.delete()


@bot.command(name="status")
@is_admin()
async def bot_status(ctx):
    """[ADMIN] Status do bot."""
    await _silent_delete(ctx)
    embed = discord.Embed(title="📊 Status", color=0x5865F2)
    embed.add_field(name="Bot", value=str(bot.user), inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="NewsAPI", value="✅" if config.NEWSAPI_KEY else "❌", inline=True)
    embed.add_field(name="Reddit RSS", value="✅ Ativo", inline=True)
    embed.add_field(name="Reset", value=f"{config.RESET_HOUR:02d}:{config.RESET_MINUTE:02d} BRT", inline=True)
    next_run = daily_news.next_iteration
    if next_run:
        embed.add_field(name="Próximo", value=next_run.astimezone(tz).strftime("%d/%m %H:%M"), inline=True)
    msg = await ctx.channel.send(embed=embed)
    await asyncio.sleep(15)
    await msg.delete()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)
