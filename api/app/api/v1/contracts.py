from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Contract
from app.schemas.core_schemas import ContractResponse


router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractResponse])
def list_contracts(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    organization_id: UUID | None = None,
    supplier_company_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[Contract]:
    query = db.query(Contract)

    if organization_id:
        query = query.filter(Contract.organization_id == organization_id)
    if supplier_company_id:
        query = query.filter(Contract.supplier_company_id == supplier_company_id)
    if status_filter:
        query = query.filter(Contract.status == status_filter)

    return query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: UUID, db: Session = Depends(get_db)) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    return contract
