from deep_translator import GoogleTranslator
from typing import Optional
import asyncio


class Translator:
    def __init__(self, target_lang: str = "pt"):
        self.target_lang = target_lang

    def _translate_sync(self, text: str) -> str:
        if not text or not text.strip():
            return text
        try:
            translator = GoogleTranslator(source="auto", target=self.target_lang)
            # GoogleTranslator tem limite de ~5000 chars por chamada
            if len(text) > 4500:
                text = text[:4500] + "..."
            result = translator.translate(text)
            return result or text
        except Exception as e:
            print(f"[Translator] Erro ao traduzir: {e}")
            return text

    async def translate(self, text: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._translate_sync(text))

    async def translate_title(self, title: str) -> str:
        return await self.translate(title)

    async def translate_description(self, description: str) -> str:
        return await self.translate(description)
