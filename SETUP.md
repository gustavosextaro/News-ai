# Setup do Bot de Notícias IA & Vibecoding

## O que você vai precisar configurar

### 1. Token do Discord (OBRIGATÓRIO)
1. Acesse [discord.com/developers/applications](https://discord.com/developers/applications)
2. Clique em **"New Application"** → dê um nome
3. Vá em **"Bot"** no menu lateral → clique **"Add Bot"**
4. Ative as permissões:
   - **MESSAGE CONTENT INTENT**
   - **SERVER MEMBERS INTENT**
5. Clique em **"Reset Token"** → copie o token
6. Cole no `.env` como `DISCORD_TOKEN=...`

### 2. Convidar o Bot para seu Servidor
1. No portal do desenvolvedor, vá em **"OAuth2" → "URL Generator"**
2. Em **Scopes**: marque `bot`
3. Em **Bot Permissions**: marque:
   - `Send Messages`
   - `Embed Links`
   - `Attach Files`
   - `Read Message History`
   - `View Channels`
4. Copie a URL gerada e abra no navegador → **Authorize**

### 3. ID do Canal (OBRIGATÓRIO)
1. No Discord, ative o **Modo Desenvolvedor**: Configurações → Avançado → Modo Desenvolvedor
2. Clique com o botão direito no canal onde quer receber as notícias
3. Clique em **"Copiar ID do canal"**
4. Cole no `.env` como `NEWS_CHANNEL_ID=...`

### 4. NewsAPI (RECOMENDADO — gratuito)
1. Acesse [newsapi.org](https://newsapi.org) → **"Get API Key"**
2. Crie uma conta gratuita
3. Copie a chave e cole no `.env` como `NEWSAPI_KEY=...`
> Plano gratuito: 100 requests/dia — suficiente para o bot

### 5. Reddit API (RECOMENDADO — gratuito)
1. Acesse [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Clique em **"create another app"**
3. Selecione **"script"**
4. Preencha nome e redirect uri como `http://localhost`
5. Copie `client_id` (abaixo do nome) e `client_secret`
6. Cole no `.env`

---

## Instalação

```bash
# Clone ou entre na pasta do projeto
cd discord-news-bot

# Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou: venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure o .env
cp .env.example .env
# Edite o .env com suas credenciais

# Rode o bot
python bot.py
```

---

## Comandos disponíveis no Discord

| Comando | O que faz |
|---------|-----------|
| `!noticias` | Posta as notícias imediatamente |
| `!proxima` | Mostra quando é a próxima atualização |
| `!status` | Status do bot e das APIs |
| `!ajuda` | Lista de comandos |

---

## Fontes de Notícias

O bot busca notícias de:
- **NewsAPI** — TechCrunch, Wired, Verge, Ars Technica, etc.
- **Reddit** — r/artificial, r/MachineLearning, r/ChatGPT, r/singularity, r/vibecoding, etc.
- **RSS Feeds** — VentureBeat AI, MIT Technology Review, The Verge AI

> ⚠️ **Twitter/X**: A API do X atualmente custa $100+/mês. O bot não inclui integração com X por padrão, mas o Reddit e NewsAPI cobrem muito bem o conteúdo viral do X através de reposts e artigos.

---

## Funcionamento

- **Reset automático**: Todo dia às 17:00 (horário de Brasília)
- **Tradução automática**: Todas as notícias são traduzidas para Português via Google Translate (gratuito, sem chave)
- **Deduplicação**: O bot remove notícias duplicadas automaticamente
- **Imagens**: Quando disponível, a imagem da notícia é exibida no embed
