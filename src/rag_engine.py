# -*- coding: utf-8 -*-
"""
MÓDULO A — Motor RAG (Retrieval-Augmented Generation) Normativo
===============================================================
Construye un índice vectorial (TF-IDF) sobre:
  1) Las disposiciones estructuradas y verificadas (legal_kb.PROVISIONS)
  2) El corpus legal crudo (corpus/*.txt) dividido en pasajes

Expone `LegalRAG.search(query, top_k)` que devuelve pasajes relevantes con
su cita (norma + artículo) para fundamentar respuestas del agente.

No requiere servicios externos: el índice se construye en memoria.
"""
from __future__ import annotations

import os
import re
import glob
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import List, Dict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from legal_kb import PROVISIONS, NORMAS

CORPUS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")

# Mapa de archivo crudo -> norma (para citar)
CORPUS_FILES = {
    "LGDFS.txt": "LGDFS",
    "Reglamento_LGDFS.txt": "RLGDFS",
    "NOM-005-SEMARNAT-1997.txt": "NOM-005",
    "NOM-059-SEMARNAT-2010.txt": "NOM-059",
    "NOM-152-SEMARNAT-2023.txt": "NOM-152",
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _clean(s: str) -> str:
    s = s.replace("\u00ad", "").replace("\f", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

_STOPWORDS = {
    "de","la","el","los","las","un","una","y","o","u","para","por","con","en","que",
    "cual","cuales","es","son","del","al","se","su","sus","como","mas","más","e","i",
    "no","si","sí","lo","le","les","me","te","nos","the","of","a","ante","bajo","sobre",
    "entre","hasta","desde","cuando","donde","cual","cuyo","esta","este","estos","estas",
    "muy","ya","tan","tanto","cada","otro","otra","todo","toda","ser","estar","haber",
}


@dataclass
class Passage:
    id: str
    norma: str
    cita: str
    texto: str
    fuente: str = ""
    temas: List[str] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


class LegalRAG:
    """Índice TF-IDF sobre disposiciones estructuradas + corpus crudo."""

    def __init__(self, build_raw: bool = True):
        self.passages: List[Passage] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self._load_structured()
        if build_raw:
            self._load_raw_corpus()
        self._build_index()

    # ------------------------------------------------------------------
    def _load_structured(self):
        for p in PROVISIONS:
            fuente = NORMAS.get(p["norma"], {}).get("fuente", "")
            self.passages.append(Passage(
                id=p["id"],
                norma=p["norma"],
                cita=f"{NORMAS.get(p['norma'], {}).get('nombre', p['norma'])} — {p['articulo']}: {p['titulo']}",
                texto=_clean(p["texto"]),
                fuente=fuente,
                temas=p.get("temas", []),
            ))

    # ------------------------------------------------------------------
    def _load_raw_corpus(self):
        """Divide el corpus crudo en pasajes por artículo/numeral."""
        for fname, norma in CORPUS_FILES.items():
            path = os.path.join(CORPUS_DIR, fname)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                raw = fh.read()
            raw = raw.replace("\u00ad", "").replace("\f", "\n")
            # separar por artículos/numerales
            chunks = re.split(r"(?=\bArt[íi]culo\s+\d+\.|\bNumeral\s+\d+\.\d|\b\d+\.\d+\.\s)", raw)
            for i, ch in enumerate(chunks):
                txt = _clean(ch)
                if len(txt) < 120:
                    continue
                # Filtrar considerandos/transitorios y texto boilerplate
                low = _strip_accents(txt.lower())
                if any(k in low for k in [
                    "mejora regulatoria", "propuesta regulatoria", "considerando",
                    "transitorio", "diario oficial de la federacion el",
                    "costo de cumplimiento",
                ]):
                    continue
                # cita aproximada
                m = re.search(r"(Art[íi]culo\s+\d+[^\n\.]*\.)", txt)
                if m:
                    cita = f"{NORMAS.get(norma, {}).get('nombre', norma)} — {m.group(1)}"
                else:
                    m2 = re.search(r"^(\d+\.\d+(?:\.\d+)?)", txt)
                    cita = f"{NORMAS.get(norma, {}).get('nombre', norma)} — num. {m2.group(1)}" if m2 else \
                           f"{NORMAS.get(norma, {}).get('nombre', norma)}"
                self.passages.append(Passage(
                    id=f"{norma}-raw-{i}",
                    norma=norma,
                    cita=cita,
                    texto=txt[:1800],
                    fuente=NORMAS.get(norma, {}).get("fuente", ""),
                    temas=[],
                ))

    # ------------------------------------------------------------------
    def _build_index(self):
        # El texto indexado combina texto + temas + cita para mejorar recall
        docs = []
        for p in self.passages:
            docs.append(_strip_accents((p.texto + " " + " ".join(p.temas) + " " + p.cita).lower()))
        self.vectorizer = TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=1, max_df=0.95,
            sublinear_tf=True, stop_words=None,
        )
        self.matrix = self.vectorizer.fit_transform(docs)

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> List[Passage]:
        if not query.strip():
            return []
        q = _strip_accents(query.lower())
        qv = self.vectorizer.transform([q])
        sims = cosine_similarity(qv, self.matrix).flatten()
        # Prioriza disposiciones estructuradas (match de temas exacto)
        q_tokens = set(re.findall(r"[a-z]+", q)) - _STOPWORDS
        for i, p in enumerate(self.passages):
            if p.temas:
                # Las disposiciones estructuradas y verificadas tienen prioridad
                sims[i] += 0.08
                tema_tokens = set()
                for t in p.temas:
                    tema_tokens |= set(re.findall(r"[a-z]+", _strip_accents(t.lower())))
                overlap = len(q_tokens & (tema_tokens - _STOPWORDS))
                sims[i] += 0.06 * overlap
        order = sims.argsort()[::-1][:top_k]
        results = []
        for idx in order:
            if sims[idx] <= 0:
                continue
            p = self.passages[idx]
            p2 = Passage(**{**p.to_dict(), "score": float(round(sims[idx], 4))})
            results.append(p2)
        return results

    # ------------------------------------------------------------------
    def answer_context(self, query: str, top_k: int = 4) -> Dict:
        """Devuelve un bloque de contexto citado listo para un LLM."""
        hits = self.search(query, top_k=top_k)
        fuentes = []
        bloques = []
        for h in hits:
            bloques.append(f"[{h.cita}]\n{h.texto}")
            if h.fuente and h.fuente not in fuentes:
                fuentes.append(h.fuente)
        return {
            "query": query,
            "contexto": "\n\n".join(bloques),
            "citas": [{"cita": h.cita, "score": h.score} for h in hits],
            "fuentes": fuentes,
        }


# Instancia perezosa (singleton)
_RAG: LegalRAG | None = None


def get_rag() -> LegalRAG:
    global _RAG
    if _RAG is None:
        _RAG = LegalRAG()
    return _RAG


if __name__ == "__main__":
    rag = get_rag()
    print(f"Pasajes indexados: {len(rag.passages)}")
    for q in [
        "¿Se requiere autorización para aprovechar tallos de Yucca?",
        "¿Cuál es el ciclo de corta de la palmilla?",
        "¿Qué debe contener el programa de manejo simplificado?",
        "¿Qué pasa si el predio está en un área natural protegida?",
        "¿Qué porcentaje de individuos maduros puedo aprovechar?",
    ]:
        print("\n" + "=" * 70)
        print("Q:", q)
        for h in rag.search(q, top_k=3):
            print(f"  [{h.score:.3f}] {h.cita}")
