from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Expense
from app.schemas.core_schemas import ExpenseResponse


router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseResponse])
def list_expenses(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    organization_id: UUID | None = None,
    person_id: UUID | None = None,
    company_id: UUID | None = None,
    contract_id: UUID | None = None,
    fiscal_year: int | None = None,
    state_code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Expense]:
    query = db.query(Expense)

    if organization_id:
        query = query.filter(Expense.organization_id == organization_id)
    if person_id:
        query = query.filter(Expense.person_id == person_id)
    if company_id:
        query = query.filter(Expense.company_id == company_id)
    if contract_id:
        query = query.filter(Expense.contract_id == contract_id)
    if fiscal_year:
        query = query.filter(Expense.fiscal_year == fiscal_year)
    if state_code:
        query = query.filter(Expense.state_code == state_code.upper())
    if date_from:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to:
        query = query.filter(Expense.expense_date <= date_to)

    return query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: UUID, db: Session = Depends(get_db)) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found.",
        )

    return expense
