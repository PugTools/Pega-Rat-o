from typing import Any

from fastapi import APIRouter, Query

from app.db.elasticsearch_db import es_client


router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(min_length=2),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    response = es_client.search(
        index="ongp_companies,ongp_contracts",
        size=limit,
        query={
            "multi_match": {
                "query": q,
                "fields": [
                    "legal_name^3",
                    "trade_name^2",
                    "cnpj^3",
                    "contract_number^3",
                    "process_number^2",
                    "object",
                    "status",
                ],
                "fuzziness": "AUTO",
            }
        },
    )
    return {
        "query": q,
        "total": response["hits"]["total"],
        "items": [
            {
                "id": hit["_id"],
                "index": hit["_index"],
                "score": hit["_score"],
                "source": hit["_source"],
            }
            for hit in response["hits"]["hits"]
        ],
    }
