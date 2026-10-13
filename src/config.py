# -*- coding: utf-8 -*-
"""
CONFIGURACIÓN — Persistencia de la API key de Gemini y ajustes
==============================================================
Guarda la configuración en `config.json` en la raíz del proyecto
(NO se sube a GitHub; está en .gitignore).

Orden de resolución de la API key:
  1) Variable de entorno GEMINI_API_KEY
  2) config.json (guardada desde la interfaz o el instalador)
"""
from __future__ import annotations

import os
import json
from typing import Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

_DEFAULTS: Dict = {
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
}


def _cargar() -> Dict:
    data = dict(_DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                data.update(json.load(fh) or {})
        except Exception:  # noqa: BLE001
            pass
    return data


def _guardar(data: Dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_PATH, 0o600)  # solo el usuario puede leerlo
    except Exception:  # noqa: BLE001
        pass


def get_api_key() -> str:
    env = os.environ.get("GEMINI_API_KEY", "").strip()
    if env:
        return env
    return (_cargar().get("gemini_api_key") or "").strip()


def set_api_key(key: str) -> None:
    data = _cargar()
    data["gemini_api_key"] = (key or "").strip()
    _guardar(data)


def get_model() -> str:
    env = os.environ.get("GEMINI_MODEL", "").strip()
    if env:
        return env
    return _cargar().get("gemini_model") or _DEFAULTS["gemini_model"]


def set_model(model: str) -> None:
    data = _cargar()
    data["gemini_model"] = (model or "").strip() or _DEFAULTS["gemini_model"]
    _guardar(data)


def estado() -> Dict:
    """Devuelve el estado de configuración (sin exponer la key completa)."""
    key = get_api_key()
    enmascarada = (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("(definida)" if key else "")
    return {
        "configurado": bool(key),
        "api_key_enmascarada": enmascarada,
        "modelo": get_model(),
        "fuente": "env" if os.environ.get("GEMINI_API_KEY") else ("config" if key else "ninguna"),
    }
