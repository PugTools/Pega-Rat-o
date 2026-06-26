from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.models import Company, Contract, Expense, RawDocument
from app.schemas.core_schemas import ContractDetailResponse, ContractResponse, ExpenseResponse


router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractResponse])
def list_contracts(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    q: str | None = None,
    organization_id: UUID | None = None,
    supplier_company_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[Contract]:
    query = db.query(Contract).options(
        selectinload(Contract.supplier),
        selectinload(Contract.organization),
    )

    if q:
        query = query.filter(
            or_(
                Contract.contract_number.ilike(f"%{q}%"),
                Contract.process_number.ilike(f"%{q}%"),
                Contract.object.ilike(f"%{q}%"),
            )
        )
    if organization_id:
        query = query.filter(Contract.organization_id == organization_id)
    if supplier_company_id:
        query = query.filter(Contract.supplier_company_id == supplier_company_id)
    if status_filter:
        query = query.filter(Contract.status == status_filter)

    return query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/paginated")
def list_contracts_paginated(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    q: str | None = None,
    organization_id: UUID | None = None,
    supplier_company_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> dict:
    skip = (page - 1) * limit
    query = _apply_contract_filters(
        db.query(Contract).options(
            selectinload(Contract.supplier),
            selectinload(Contract.organization),
        ),
        q=q,
        organization_id=organization_id,
        supplier_company_id=supplier_company_id,
        status_filter=status_filter,
    )
    count_query = _apply_contract_filters(
        db.query(Contract.id),
        q=q,
        organization_id=organization_id,
        supplier_company_id=supplier_company_id,
        status_filter=status_filter,
    )
    total = count_query.order_by(None).count()
    total_value = _contract_total_value(
        db=db,
        q=q,
        organization_id=organization_id,
        supplier_company_id=supplier_company_id,
        status_filter=status_filter,
    )
    contracts = (
        query.order_by(Contract.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            ContractResponse.model_validate(contract).model_dump(mode="json")
            for contract in contracts
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "pages": max(1, (total + limit - 1) // limit),
        "has_next": skip + limit < total,
        "has_previous": page > 1,
        "total_value": str(total_value or 0),
        "statuses": _contract_status_counts(db),
    }


@router.get("/{contract_id}", response_model=ContractDetailResponse)
def get_contract(contract_id: UUID, db: Session = Depends(get_db)) -> dict:
    contract = (
        db.query(Contract)
        .options(
            selectinload(Contract.supplier),
            selectinload(Contract.organization),
        )
        .filter(Contract.id == contract_id)
        .one_or_none()
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    payload = ContractResponse.model_validate(contract).model_dump(mode="json")
    expense_rows = (
        db.query(Expense, Company, RawDocument)
        .outerjoin(Company, Expense.company_id == Company.id)
        .outerjoin(RawDocument, Expense.raw_document_id == RawDocument.id)
        .filter(Expense.contract_id == contract_id)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(50)
        .all()
    )
    payload["supplier"] = (
        {
            "id": str(contract.supplier.id),
            "legal_name": contract.supplier.legal_name,
            "trade_name": contract.supplier.trade_name,
            "cnpj": contract.supplier.cnpj,
            "cnae": contract.supplier.cnae,
            "city": contract.supplier.city,
            "state_code": contract.supplier.state_code,
            "registration_status": contract.supplier.registration_status,
            "source_id": str(contract.supplier.source_id) if contract.supplier.source_id else None,
            "created_at": contract.supplier.created_at.isoformat(),
        }
        if contract.supplier
        else None
    )
    payload["organization"] = (
        {
            "id": str(contract.organization.id),
            "name": contract.organization.name,
            "normalized_name": contract.organization.normalized_name,
            "cnpj": contract.organization.cnpj,
            "organization_type": contract.organization.organization_type,
            "jurisdiction_level": contract.organization.jurisdiction_level,
            "state_code": contract.organization.state_code,
            "municipality_code": contract.organization.municipality_code,
        }
        if contract.organization
        else None
    )
    payload["expenses"] = [_expense_payload(*row) for row in expense_rows]
    payload["expense_total"] = str(sum((expense.amount or 0) for expense, _, _ in expense_rows))
    return payload


def _apply_contract_filters(
    query,
    *,
    q: str | None,
    organization_id: UUID | None,
    supplier_company_id: UUID | None,
    status_filter: str | None,
):
    if q:
        query = query.filter(
            or_(
                Contract.contract_number.ilike(f"%{q}%"),
                Contract.process_number.ilike(f"%{q}%"),
                Contract.object.ilike(f"%{q}%"),
            )
        )
    if organization_id:
        query = query.filter(Contract.organization_id == organization_id)
    if supplier_company_id:
        query = query.filter(Contract.supplier_company_id == supplier_company_id)
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    return query


def _contract_total_value(
    db: Session,
    *,
    q: str | None,
    organization_id: UUID | None,
    supplier_company_id: UUID | None,
    status_filter: str | None,
):
    query = _apply_contract_filters(
        db.query(func.coalesce(func.sum(Contract.total_value), 0)),
        q=q,
        organization_id=organization_id,
        supplier_company_id=supplier_company_id,
        status_filter=status_filter,
    )
    return query.scalar()


def _contract_status_counts(db: Session) -> list[dict]:
    rows = (
        db.query(Contract.status, func.count(Contract.id))
        .group_by(Contract.status)
        .order_by(func.count(Contract.id).desc(), Contract.status)
        .all()
    )
    return [
        {
            "status": str(status_value or "sem_status"),
            "label": str(status_value or "Sem status"),
            "total": int(total or 0),
        }
        for status_value, total in rows
    ]


def _expense_payload(
    expense: Expense,
    supplier: Company | None,
    raw_document: RawDocument | None,
) -> dict:
    payload = ExpenseResponse.model_validate(expense).model_dump(mode="json")
    payload["supplier_company_id"] = str(supplier.id) if supplier else (
        str(expense.company_id) if expense.company_id else None
    )
    payload["supplier_name"] = supplier.legal_name if supplier else None
    payload["supplier_cnpj"] = supplier.cnpj if supplier else None
    payload["document_url"] = _document_url(raw_document)
    return payload


def _document_url(raw_document: RawDocument | None) -> str | None:
    if raw_document is None:
        return None

    metadata = raw_document.metadata_json or {}
    for key in ("document_url", "official_url", "url", "source_url", "nota_fiscal_url"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return raw_document.original_url or raw_document.storage_uri
