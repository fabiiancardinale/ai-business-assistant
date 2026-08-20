import os
import json
import requests


# =========================================================
# GROQ EN VEZ DE OLLAMA LOCAL
#
# Antes esto llamaba a Ollama corriendo en la propia VPS
# (http://127.0.0.1:11434), que al no tener GPU generaba texto
# lento (CPU pura). Groq corre los modelos en su propio hardware
# especializado (LPU) y responde mucho más rápido, cobrando por
# token usado en vez de por servidor.
#
# La API de Groq es compatible con el formato de OpenAI, por eso
# el body usa "messages" en vez del "prompt" plano que usaba
# Ollama.
#
# IMPORTANTE: la API key NO va escrita acá en el código. Se lee
# de la variable de entorno GROQ_API_KEY, que hay que configurar
# en la VPS con:
#
#   sudo systemctl edit ai-business-assistant.service
#
# Y agregar, dentro de [Service]:
#
#   Environment="GROQ_API_KEY=tu_api_key_de_groq"
#
# Después: sudo systemctl daemon-reload && sudo systemctl restart ai-business-assistant.service
# =========================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Llama 3.3 70B: el modelo más grande/completo que ofrece Groq sin
# ser "enterprise". Buena calidad de respuesta, todavía barato
# (USD 0.59 / 0.79 por millón de tokens de entrada/salida). Si en
# algún momento se quiere priorizar costo por sobre calidad, se
# puede cambiar a "llama-3.1-8b-instant" (mucho más barato y
# todavía más rápido, pero respuestas más simples).
MODEL = "llama-3.3-70b-versatile"

# Máximo de tokens que genera por respuesta. Ver la nota en el
# prompt (main.py) que le pide al modelo ser breve — entre las dos
# cosas, la respuesta debería terminar sola antes de este límite
# en la gran mayoría de los casos.
MAX_TOKENS = 450


def _headers():

    if not GROQ_API_KEY:

        raise RuntimeError(
            "Falta configurar la variable de entorno GROQ_API_KEY "
            "en la VPS (ver systemctl edit ai-business-assistant.service)."
        )

    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }


def generate_response(prompt: str) -> str:
    """
    Envía el prompt (ya armado completo por quien llama a esta función,
    por ejemplo main.py) a Groq y espera la respuesta completa antes
    de devolverla. Se usa donde no hace falta mostrar el texto apareciendo
    en tiempo real (por ejemplo, el endpoint interno /chat del panel).
    """

    response = requests.post(
        GROQ_URL,
        headers=_headers(),
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "max_tokens": MAX_TOKENS
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def stream_response(prompt: str):
    """
    Igual que generate_response, pero en vez de esperar la respuesta
    completa, va entregando (yield) el texto a medida que Groq lo
    genera. Se usa en el endpoint público /api/chat para que el widget
    muestre el texto apareciendo en tiempo real.

    Groq entrega el stream en formato "Server-Sent Events": cada
    línea empieza con "data: " seguido de un JSON, y termina con una
    línea "data: [DONE]".
    """

    with requests.post(
        GROQ_URL,
        headers=_headers(),
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": True,
            "max_tokens": MAX_TOKENS
        },
        timeout=60,
        stream=True
    ) as response:

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            decoded = line.decode("utf-8")

            if not decoded.startswith("data: "):
                continue

            payload = decoded[len("data: "):]

            if payload == "[DONE]":
                break

            chunk = json.loads(payload)

            delta = (
                chunk.get("choices", [{}])[0]
                .get("delta", {})
                .get("content", "")
            )

            if delta:
                yield delta
