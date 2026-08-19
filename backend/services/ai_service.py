import json
import requests


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# qwen3:1.7b en vez de qwen3:4b: el servidor no tiene GPU, corre todo
# en CPU (4 núcleos), y un modelo más chico genera texto bastante más
# rápido (menos parámetros que calcular por cada token). La respuesta
# es un poco menos elaborada, pero para responder preguntas de atención
# al cliente con la información de la empresa alcanza de sobra.
#
# IMPORTANTE: antes de reiniciar el servicio hay que descargar el
# modelo en la VPS una sola vez con:
#
#   ollama pull qwen3:1.7b
#
MODEL = "qwen3:1.7b"

# Cuánto tiempo mantiene Ollama el modelo cargado en memoria entre
# consultas. Sin esto, cada mensaje puede perder tiempo extra recargando
# el modelo si pasó un rato desde la última consulta.
KEEP_ALIVE = "30m"

# Máximo de tokens que genera por respuesta. Respuestas más cortas
# terminan de generarse más rápido, pero un límite muy justo corta
# la respuesta a mitad de palabra si el modelo se extiende. 450 da
# más margen; junto con la regla de "sé breve" en el prompt, la
# mayoría de las respuestas van a terminar solas antes de llegar
# al límite.
MAX_TOKENS = 450


def generate_response(prompt: str) -> str:
    """
    Envía el prompt (ya armado completo por quien llama a esta función,
    por ejemplo main.py) a Ollama y espera la respuesta completa antes
    de devolverla. Se usa donde no hace falta mostrar el texto apareciendo
    en tiempo real (por ejemplo, el endpoint interno /chat del panel).

    IMPORTANTE: esta función ya NO arma su propio prompt con la
    información de la empresa — antes lo hacía, y como quien llama
    también arma un prompt con esa misma información, terminaba
    mandándose duplicada a Ollama. Ahora se manda una sola vez.
    """

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {
                "num_predict": MAX_TOKENS
            }
        },
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    return data["response"].strip()


def stream_response(prompt: str):
    """
    Igual que generate_response, pero en vez de esperar la respuesta
    completa, va entregando (yield) el texto a medida que Ollama lo
    genera. Se usa en el endpoint público /api/chat para que el widget
    muestre el texto apareciendo en tiempo real en vez de quedar 30-90
    segundos en silencio.
    """

    with requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": True,
            "keep_alive": KEEP_ALIVE,
            "options": {
                "num_predict": MAX_TOKENS
            }
        },
        timeout=180,
        stream=True
    ) as response:

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            chunk = json.loads(line)

            piece = chunk.get("response", "")

            if piece:
                yield piece

            if chunk.get("done"):
                break