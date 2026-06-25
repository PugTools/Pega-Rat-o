from fastapi import APIRouter, HTTPException, Query, status

from app.modules.graphs.sync_service import GraphSyncService


router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.get("/entity/{entity_type}/{entity_id}")
def get_entity_graph(
    entity_type: str,
    entity_id: str,
    depth: int = Query(default=2, ge=1, le=2),
) -> dict[str, list[dict]]:
    service = GraphSyncService()

    try:
        graph = service.get_entity_neighborhood(
            entity_type=entity_type,
            entity_id=entity_id,
            depth=depth,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return graph
