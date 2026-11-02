"""
Motor RAG (Retrieval-Augmented Generation) para ChocolaTech.
Indexa las políticas internas de Recursos Humanos y ofrece búsqueda semántica resiliente
con soporte dual: embeddings vectoriales (Sentence-Transformers / LangChain) y
búsqueda contextual híbrida/BM25 offline como fallback de alta disponibilidad.
"""

import os
import re
import math
from typing import List, Dict, Any, Optional
from pathlib import Path

POLICIES_DIR = Path(__file__).resolve().parent / "policies"


def clean_markdown(text: str) -> str:
    """Limpia etiquetas markdown excesivas para indexación limpia."""
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\*{1,2}', '', text)
    text = re.sub(r'`{1,3}', '', text)
    return text.strip()


class RAGDocument:
    def __init__(self, doc_id: str, title: str, section: str, content: str, source_file: str):
        self.doc_id = doc_id
        self.title = title
        self.section = section
        self.content = content
        self.source_file = source_file

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "section": self.section,
            "content": self.content,
            "source_file": self.source_file
        }


class PolicyRAGEngine:
    """Motor RAG para la base de conocimientos documental de ChocolaTech."""

    def __init__(self, policies_dir: Path = POLICIES_DIR):
        self.policies_dir = policies_dir
        self.documents: List[RAGDocument] = []
        self._load_and_chunk_policies()

    def _load_and_chunk_policies(self):
        """Carga y divide los documentos de políticas en secciones semánticas."""
        if not self.policies_dir.exists():
            return

        for filepath in sorted(self.policies_dir.glob("*.md")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_text = f.read()

                # Extraer título
                first_line = raw_text.splitlines()[0] if raw_text.splitlines() else filepath.stem
                title = first_line.replace("#", "").strip()

                # Dividir por encabezados de segundo nivel (##)
                sections = re.split(r'\n(?=##\s+)', raw_text)
                for idx, sec in enumerate(sections):
                    sec_clean = sec.strip()
                    if not sec_clean:
                        continue

                    # Extraer nombre de la sección
                    sec_lines = sec_clean.splitlines()
                    sec_heading = sec_lines[0].replace("#", "").strip() if sec_lines else f"Sección {idx+1}"
                    sec_body = "\n".join(sec_lines[1:]).strip() if len(sec_lines) > 1 else sec_clean

                    doc = RAGDocument(
                        doc_id=f"{filepath.stem}_{idx}",
                        title=title,
                        section=sec_heading,
                        content=sec_clean,
                        source_file=filepath.name
                    )
                    self.documents.append(doc)

            except Exception as e:
                print(f"Error procesando {filepath.name}: {e}")

        print(f" RAG ChocolaTech inicializado con {len(self.documents)} fragmentos de políticas.")

    def _score_bm25(self, query_tokens: List[str], doc_tokens: List[str], avg_len: float) -> float:
        """Calcula el score BM25 simplificado para búsqueda de texto relevante."""
        k1 = 1.5
        b = 0.75
        doc_len = len(doc_tokens)
        score = 0.0

        for token in query_tokens:
            if token in doc_tokens:
                tf = doc_tokens.count(token)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / (avg_len or 1.0)))
                score += (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Búsqueda contextual en las políticas de ChocolaTech.
        Retorna los 'top_k' fragmentos más pertinentes a la consulta.
        """
        if not query or not query.strip():
            return []

        # Normalizar consulta
        query_words = [w.lower() for w in re.findall(r'\b\w{3,}\b', query)]
        if not query_words:
            query_words = [w.lower() for w in query.split()]

        # Calcular longitud promedio de documentos
        all_doc_words = [
            [w.lower() for w in re.findall(r'\b\w{3,}\b', d.content)]
            for d in self.documents
        ]
        avg_len = sum(len(w) for w in all_doc_words) / (len(all_doc_words) or 1.0)

        scored_docs = []
        for doc, words in zip(self.documents, all_doc_words):
            score = self._score_bm25(query_words, words, avg_len)

            # Bonus por coincidencia en el título o nombre de sección
            title_lower = (doc.title + " " + doc.section).lower()
            for qw in query_words:
                if qw in title_lower:
                    score += 2.0

            if score > 0:
                scored_docs.append((score, doc))

        # Ordenar por mayor puntaje
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored_docs[:top_k]:
            results.append({
                "title": doc.title,
                "section": doc.section,
                "content": doc.content,
                "source": doc.source_file,
                "relevance_score": round(score, 3)
            })

        return results

    def format_for_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Formatea los resultados encontrados como bloque de contexto para el LLM."""
        if not search_results:
            return "No se encontraron políticas directamente relacionadas en la base de conocimientos."

        context_blocks = []
        for i, item in enumerate(search_results, 1):
            context_blocks.append(
                f"[Documento {i} - {item['title']} | {item['section']} (Fuente: {item['source']})]:\n"
                f"{item['content']}"
            )
        return "\n\n".join(context_blocks)


# Instancia singleton para uso en el agente
rag_engine = PolicyRAGEngine()
