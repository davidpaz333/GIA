"""
TFG3 - Llamada de prueba a un modelo pequeño local (Ollama) a través de LiteLLM.

Pide al modelo que implemente un G-Counter y mide tokens y latencia.
Solo usa modelos locales y gratuitos: no se llama a ninguna API de pago.

Requisitos:
    - Ollama arrancado y con el modelo descargado (p. ej. `ollama pull <modelo>`).
    - litellm con versión fijada (1.82.6; las 1.82.7 y 1.82.8 eran maliciosas).

Uso:
    python call_local_llm.py
    python call_local_llm.py --model qwen2.5-coder:1.5b --out llm_call.json
"""

import argparse
import json
import os
import time
from importlib.metadata import version
from pathlib import Path

# LiteLLM descarga por defecto un fichero de precios desde internet al
# importarse. Con esta variable usa la copia local, así que no hace falta red
# y el resultado no depende de un fichero remoto que puede cambiar.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm  # noqa: E402  (se importa después de fijar la variable)

DEFAULT_PROMPT = (
    "Implementa en Python un G-Counter (CRDT de solo incremento) como una clase "
    "con los métodos increment(), value() y merge(other). Responde solo con código."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-coder:1.5b",
                    help="nombre del modelo tal como aparece en `ollama list`")
    ap.add_argument("--api-base", default="http://localhost:11434")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--out", default="llm_call.json")
    args = ap.parse_args()

    start = time.perf_counter()
    try:
        response = litellm.completion(
            model=f"ollama/{args.model}",
            messages=[{"role": "user", "content": args.prompt}],
            api_base=args.api_base,
            temperature=0,  # menos variación entre ejecuciones
        )
    except Exception as exc:  # noqa: BLE001 - se muestra el error tal cual
        raise SystemExit(
            f"La llamada falló: {exc}\n"
            "Comprueba que Ollama está arrancado (ollama list) y que el modelo existe."
        )
    latency = time.perf_counter() - start

    usage = response.usage
    # Para un modelo local no hay precio: LiteLLM puede no tenerlo en su tabla.
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:  # noqa: BLE001
        cost = None

    result = {
        "litellm_version": version("litellm"),
        "model": args.model,
        "prompt": args.prompt,
        "latency_seconds": round(latency, 3),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "completion_tokens_per_second": round(usage.completion_tokens / latency, 2),
        "cost_usd": cost,
        "response": response.choices[0].message.content,
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False),
                              encoding="utf-8")

    print(f"Escrito {args.out}")
    print(f"  modelo: {args.model} | LiteLLM {result['litellm_version']}")
    print(f"  latencia: {result['latency_seconds']} s")
    print(f"  tokens: {result['prompt_tokens']} entrada + "
          f"{result['completion_tokens']} salida = {result['total_tokens']}")
    print(f"  velocidad: {result['completion_tokens_per_second']} tokens/s")


if __name__ == "__main__":
    main()
