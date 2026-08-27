"""Capa AIProvider — desacopla el chatbot del proveedor de IA concreto.

    AIService -> AIProvider -> (GroqAdapter | OpenAIAdapter | ...)

El resto del sistema solo llama a `generate()` / `stream()`. Cambiar de
proveedor (o agregar OpenAI/Anthropic/Gemini/Ollama) es sumar un adapter,
sin tocar la lógica de conversaciones."""
from __future__ import annotations

import json
from typing import Iterator, Protocol

import requests

from app.core.config import settings


class AIProvider(Protocol):
    name: str
    def generate(self, messages: list[dict], *, model: str, temperature: float, max_tokens: int) -> str: ...
    def stream(self, messages: list[dict], *, model: str, temperature: float, max_tokens: int) -> Iterator[str]: ...


class GroqAdapter:
    """Groq — API compatible con OpenAI (chat completions)."""
    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def generate(self, messages, *, model, temperature, max_tokens) -> str:
        r = requests.post(self.URL, headers=self._headers(), json={
            "model": model, "messages": messages, "stream": False,
            "temperature": temperature, "max_tokens": max_tokens,
        }, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def stream(self, messages, *, model, temperature, max_tokens) -> Iterator[str]:
        with requests.post(self.URL, headers=self._headers(), json={
            "model": model, "messages": messages, "stream": True,
            "temperature": temperature, "max_tokens": max_tokens,
        }, timeout=60, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if not decoded.startswith("data: "):
                    continue
                payload = decoded[len("data: "):]
                if payload == "[DONE]":
                    break
                try:
                    delta = json.loads(payload)["choices"][0].get("delta", {}).get("content", "")
                except Exception:
                    delta = ""
                if delta:
                    yield delta


class EchoAdapter:
    """Fallback cuando no hay API key configurada (desarrollo). No llama a
    ningún servicio: responde algo útil para poder probar el flujo sin IA."""
    name = "echo"

    def generate(self, messages, *, model, temperature, max_tokens) -> str:
        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        return ("Estoy en modo demo (falta configurar la API key de IA). "
                f"Recibí tu mensaje: “{last_user}”. Cuando se configure la "
                "clave, responderé con IA usando la info del negocio.")

    def stream(self, messages, *, model, temperature, max_tokens) -> Iterator[str]:
        yield self.generate(messages, model=model, temperature=temperature, max_tokens=max_tokens)


def get_provider() -> AIProvider:
    """Devuelve el proveedor configurado. Si falta la key, cae a EchoAdapter
    para no romper el flujo (y avisar en la respuesta)."""
    provider = (settings.AI_PROVIDER or "groq").lower()
    if provider == "groq" and settings.GROQ_API_KEY:
        return GroqAdapter(settings.GROQ_API_KEY)
    # (acá se agregarían OpenAIAdapter, AnthropicAdapter, etc.)
    return EchoAdapter()
