from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceBase(BaseModel):
    name: str
    scope: str
    jurisdiction: str | None = None
    base_url: str | None = None
    source_type: str
    legal_basis: str | None = None
    active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceResponse(SourceBase, ORMModel):
    id: UUID
    created_at: datetime


class PersonBase(BaseModel):
    full_name: str
    normalized_name: str
    masked_cpf: str | None = None
    birth_year: int | None = None
    data_origin: str | None = None
    external_id: str | None = None
    party_acronym: str | None = None
    state_code: str | None = None
    photo_url: str | None = None
    email: str | None = None
    latest_expense_total: Decimal | None = None
    latest_expense_year: int | None = None
    declared_assets_value: Decimal | None = None
    declared_assets_year: int | None = None
    salary_reference_value: Decimal | None = None
    salary_reference_year: int | None = None
    salary_reference_source: str | None = None
    asset_salary_ratio: Decimal | None = None


class PersonCreate(PersonBase):
    pass


class PersonRoleResponse(ORMModel):
    id: UUID
    role_name: str
    branch: str | None = None
    jurisdiction_level: str | None = None
    state_code: str | None = None
    municipality_code: str | None = None
    party_acronym: str | None = None
    organization_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class PersonResponse(PersonBase, ORMModel):
    id: UUID
    created_at: datetime
    roles: list[PersonRoleResponse] = Field(default_factory=list)


class OrganizationBase(BaseModel):
    name: str
    normalized_name: str
    cnpj: str | None = None
    organization_type: str | None = None
    jurisdiction_level: str | None = None
    state_code: str | None = None
    municipality_code: str | None = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase, ORMModel):
    id: UUID


class PublicRoleBase(BaseModel):
    person_id: UUID
    role_name: str
    branch: str | None = None
    jurisdiction_level: str | None = None
    state_code: str | None = None
    municipality_code: str | None = None
    party_acronym: str | None = None
    organization_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    source_id: UUID | None = None


class PublicRoleCreate(PublicRoleBase):
    pass


class PublicRoleResponse(PublicRoleBase, ORMModel):
    id: UUID


class CompanyBase(BaseModel):
    legal_name: str
    trade_name: str | None = None
    cnpj: str
    cnae: str | None = None
    city: str | None = None
    state_code: str | None = None
    registration_status: str | None = None
    source_id: UUID | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    cnpj: str | None = None
    cnae: str | None = None
    city: str | None = None
    state_code: str | None = None
    registration_status: str | None = None
    source_id: UUID | None = None


class CompanyResponse(CompanyBase, ORMModel):
    id: UUID
    created_at: datetime


class ContractBase(BaseModel):
    contract_number: str | None = None
    process_number: str | None = None
    organization_id: UUID | None = None
    supplier_company_id: UUID | None = None
    object: str | None = None
    modality: str | None = None
    status: str | None = None
    signed_at: date | None = None
    starts_at: date | None = None
    ends_at: date | None = None
    total_value: Decimal | None = None
    source_id: UUID | None = None
    raw_document_id: UUID | None = None
    supplier_payload: CompanyCreate | None = Field(default=None, exclude=True)
    organization_payload: OrganizationCreate | None = Field(default=None, exclude=True)


class ContractCreate(ContractBase):
    pass


class ContractResponse(ContractBase, ORMModel):
    id: UUID
    created_at: datetime
    supplier: CompanyResponse | None = None
    organization: OrganizationResponse | None = None


class ExpenseBase(BaseModel):
    organization_id: UUID | None = None
    person_id: UUID | None = None
    company_id: UUID | None = None
    contract_id: UUID | None = None
    expense_type: str | None = None
    description: str | None = None
    commitment_number: str | None = None
    liquidation_number: str | None = None
    payment_number: str | None = None
    amount: Decimal
    expense_date: date
    fiscal_year: int
    state_code: str | None = None
    municipality_code: str | None = None
    source_id: UUID | None = None
    raw_document_id: UUID | None = None


class ExpenseCreate(ExpenseBase):
    supplier_payload: CompanyCreate | None = Field(default=None, exclude=True)
    document_url: str | None = Field(default=None, exclude=True)


class ExpenseResponse(ExpenseBase, ORMModel):
    id: UUID
    created_at: datetime
    supplier_company_id: UUID | None = None
    supplier_name: str | None = None
    supplier_cnpj: str | None = None
    document_url: str | None = None


class PersonDetailResponse(PersonResponse):
    recent_expenses: list[ExpenseResponse] = Field(default_factory=list)
    expense_total: Decimal | None = None


class ContractDetailResponse(ContractResponse):
    expenses: list[ExpenseResponse] = Field(default_factory=list)
    expense_total: Decimal | None = None


class RiskAlertResponse(ORMModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    alert_type: str
    severity: str
    score: Decimal
    title: str
    explanation: str
    evidence: dict
    status: str
    created_at: datetime
