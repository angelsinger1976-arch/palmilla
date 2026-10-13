# -*- coding: utf-8 -*-
"""
CLIENTE GEMINI — Integración con Google Gemini (IA generativa)
==============================================================
Envuelve la API REST de Google Gemini (generativelanguage.googleapis.com)
para generar respuestas del agente "Ingeniero Forestal" a partir del
contexto legal recuperado por el Módulo A (RAG).

Diseño:
  * Sin dependencias pesadas: usa `requests` (o urllib como respaldo).
  * La API key se resuelve en este orden:
      1) Variable de entorno GEMINI_API_KEY
      2) Archivo de configuración config.json (gestionado por config.py)
      3) Valor pasado explícitamente
  * Si no hay API key, `is_configured()` devuelve False y el sistema
    funciona en modo RAG offline (sin IA generativa).
"""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict

try:
    import requests  # opcional; si no está, se usa urllib
    _HAS_REQUESTS = True
except Exception:  # noqa: BLE001
    _HAS_REQUESTS = False

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.0-flash"


def _leer_config_key() -> str:
    """Lee la API key desde config.json (si existe)."""
    try:
        from config import get_api_key  # import perezoso para evitar ciclos
        return get_api_key() or ""
    except Exception:  # noqa: BLE001
        return ""


class GeminiError(Exception):
    pass


class GeminiClient:
    """Cliente mínimo para la API de Gemini (generateContent)."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self._api_key = api_key
        self.model = model or DEFAULT_MODEL

    # ------------------------------------------------------------------
    @property
    def api_key(self) -> str:
        return (
            self._api_key
            or os.environ.get("GEMINI_API_KEY", "")
            or _leer_config_key()
        ).strip()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def set_api_key(self, key: str):
        self._api_key = (key or "").strip()

    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 60,
    ) -> str:
        """Genera texto con Gemini. Lanza GeminiError si falla."""
        key = self.api_key
        if not key:
            raise GeminiError(
                "No hay API key de Gemini configurada. Configure GEMINI_API_KEY "
                "o guárdela desde la interfaz (⚙️ Configuración)."
            )

        url = f"{API_BASE}/{self.model}:generateContent?key={key}"
        payload: Dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            if _HAS_REQUESTS:
                r = requests.post(url, data=data, headers=headers, timeout=timeout)
                if r.status_code != 200:
                    raise GeminiError(f"Gemini HTTP {r.status_code}: {r.text[:400]}")
                body = r.json()
            else:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
        except GeminiError:
            raise
        except urllib.error.HTTPError as e:  # noqa: PERF203
            detalle = e.read().decode("utf-8", "ignore")[:400]
            raise GeminiError(f"Gemini HTTP {e.code}: {detalle}") from e
        except Exception as e:  # noqa: BLE001
            raise GeminiError(f"Error de conexión con Gemini: {e}") from e

        return self._extraer_texto(body)

    # ------------------------------------------------------------------
    @staticmethod
    def _extraer_texto(body: Dict) -> str:
        try:
            cands = body.get("candidates") or []
            if not cands:
                fb = body.get("promptFeedback", {})
                raise GeminiError(f"Gemini no devolvió candidatos. {fb}")
            parts = cands[0].get("content", {}).get("parts", [])
            texto = "".join(p.get("text", "") for p in parts).strip()
            if not texto:
                raise GeminiError("Gemini devolvió una respuesta vacía.")
            return texto
        except GeminiError:
            raise
        except Exception as e:  # noqa: BLE001
            raise GeminiError(f"Respuesta inesperada de Gemini: {e}") from e

    # ------------------------------------------------------------------
    def listar_modelos(self, timeout: int = 20) -> List[str]:
        """Lista los modelos disponibles (útil para validar la API key)."""
        key = self.api_key
        if not key:
            raise GeminiError("No hay API key configurada.")
        url = f"{API_BASE}?key={key}"
        try:
            if _HAS_REQUESTS:
                r = requests.get(url, timeout=timeout)
                if r.status_code != 200:
                    raise GeminiError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
                body = r.json()
            else:
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
        except GeminiError:
            raise
        except Exception as e:  # noqa: BLE001
            raise GeminiError(f"Error al listar modelos: {e}") from e
        return [m.get("name", "") for m in body.get("models", [])]


# Instancia perezosa
_CLIENT: Optional[GeminiClient] = None


def get_gemini() -> GeminiClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = GeminiClient()
    return _CLIENT


if __name__ == "__main__":
    c = get_gemini()
    print("Configurado:", c.is_configured())
    print("Modelo:", c.model)
    if c.is_configured():
        try:
            print(c.generate("Responde solo: OK"))
        except GeminiError as e:
            print("Error:", e)
