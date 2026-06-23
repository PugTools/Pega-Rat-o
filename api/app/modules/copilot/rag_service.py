import os
from typing import Any

from openai import OpenAI

from app.db.elasticsearch_db import es_client
from app.db.neo4j_database import neo4j_connection


class CopilotRAGService:
    def __init__(self) -> None:
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None

    def answer(self, question: str) -> dict[str, Any]:
        context = self._collect_context(question)
        if self.client is None:
            return {
                "answer": self._fallback_answer(question, context),
                "sources": context,
                "mode": "local",
            }

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Voce e o copiloto investigativo do ONGP. Responda apenas "
                        "com base no contexto fornecido, separando indicios de conclusoes."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Pergunta: {question}\n\nContexto:\n{context}",
                },
            ],
            temperature=0.2,
        )
        return {
            "answer": completion.choices[0].message.content,
            "sources": context,
            "mode": "openai",
        }

    def _collect_context(self, question: str) -> dict[str, Any]:
        return {
            "search": self._search_elasticsearch(question),
            "graph": self._search_graph(question),
        }

    def _search_elasticsearch(self, question: str) -> list[dict[str, Any]]:
        try:
            response = es_client.search(
                index="ongp_companies,ongp_contracts",
                size=5,
                query={
                    "multi_match": {
                        "query": question,
                        "fields": ["legal_name^3", "trade_name", "object", "cnpj", "contract_number"],
                        "fuzziness": "AUTO",
                    }
                },
            )
            return [
                {
                    "index": hit["_index"],
                    "score": hit["_score"],
                    "source": hit["_source"],
                }
                for hit in response["hits"]["hits"]
            ]
        except Exception as exc:
            return [{"error": f"elasticsearch_unavailable: {exc}"}]

    def _search_graph(self, question: str) -> list[dict[str, Any]]:
        try:
            return neo4j_connection.execute_query(
                """
                MATCH (n)
                WHERE any(value IN [n.name, n.full_name, n.legal_name, n.object]
                          WHERE value IS NOT NULL AND toLower(value) CONTAINS toLower($q))
                OPTIONAL MATCH (n)-[r]-(m)
                RETURN labels(n)[0] AS label,
                       n.id AS id,
                       properties(n) AS properties,
                       collect(DISTINCT {type: type(r), neighbor: m.id, labels: labels(m)})[0..5] AS edges
                LIMIT 10
                """,
                {"q": question[:120]},
            )
        except Exception as exc:
            return [{"error": f"neo4j_unavailable: {exc}"}]

    def _fallback_answer(self, question: str, context: dict[str, Any]) -> str:
        search_hits = context.get("search", [])
        graph_hits = context.get("graph", [])
        return (
            f"Pergunta analisada: {question}. "
            f"Foram encontrados {len(search_hits)} resultados textuais e "
            f"{len(graph_hits)} registros de grafo para apoiar a investigacao."
        )
