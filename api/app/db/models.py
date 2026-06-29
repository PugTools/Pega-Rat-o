import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Numeric, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    companies: Mapped[list["Company"]] = relationship(back_populates="source")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="source")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="source")
    public_roles: Mapped[list["PublicRole"]] = relationship(back_populates="source")
    raw_documents: Mapped[list["RawDocument"]] = relationship(back_populates="source")


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (Index("idx_raw_documents_sha256", "sha256"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id")
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    original_url: Mapped[str | None] = mapped_column(Text)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source: Mapped["Source | None"] = relationship(back_populates="raw_documents")


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = (
        Index("idx_persons_normalized_name", "normalized_name"),
        Index("idx_persons_origin_external", "data_origin", "external_id"),
        Index("idx_persons_party_state", "party_acronym", "state_code"),
        Index("idx_persons_expense_total", "latest_expense_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    masked_cpf: Mapped[str | None] = mapped_column(Text)
    birth_year: Mapped[int | None] = mapped_column()
    data_origin: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)
    party_acronym: Mapped[str | None] = mapped_column(String(16))
    state_code: Mapped[str | None] = mapped_column(String(2))
    photo_url: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    latest_expense_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    latest_expense_year: Mapped[int | None] = mapped_column()
    declared_assets_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    declared_assets_year: Mapped[int | None] = mapped_column()
    salary_reference_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    salary_reference_year: Mapped[int | None] = mapped_column()
    salary_reference_source: Mapped[str | None] = mapped_column(Text)
    asset_salary_ratio: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    roles: Mapped[list["PublicRole"]] = relationship(back_populates="person")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="person")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    cnpj: Mapped[str | None] = mapped_column(Text)
    organization_type: Mapped[str | None] = mapped_column(Text)
    jurisdiction_level: Mapped[str | None] = mapped_column(Text)
    state_code: Mapped[str | None] = mapped_column(String(2))
    municipality_code: Mapped[str | None] = mapped_column(Text)

    roles: Mapped[list["PublicRole"]] = relationship(back_populates="organization")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="organization")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="organization")


class PublicRole(Base):
    __tablename__ = "public_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False
    )
    role_name: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str | None] = mapped_column(Text)
    jurisdiction_level: Mapped[str | None] = mapped_column(Text)
    state_code: Mapped[str | None] = mapped_column(String(2))
    municipality_code: Mapped[str | None] = mapped_column(Text)
    party_acronym: Mapped[str | None] = mapped_column(Text)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id")
    )

    person: Mapped["Person"] = relationship(back_populates="roles")
    organization: Mapped["Organization | None"] = relationship(back_populates="roles")
    source: Mapped["Source | None"] = relationship(back_populates="public_roles")


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (Index("idx_companies_cnpj", "cnpj"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    trade_name: Mapped[str | None] = mapped_column(Text)
    cnpj: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    cnae: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    state_code: Mapped[str | None] = mapped_column(String(2))
    registration_status: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source: Mapped["Source | None"] = relationship(back_populates="companies")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="supplier")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="company")


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("idx_contracts_supplier", "supplier_company_id"),
        Index("idx_contracts_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_number: Mapped[str | None] = mapped_column(Text)
    process_number: Mapped[str | None] = mapped_column(Text)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    supplier_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id")
    )
    object: Mapped[str | None] = mapped_column(Text)
    modality: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    signed_at: Mapped[date | None] = mapped_column(Date)
    starts_at: Mapped[date | None] = mapped_column(Date)
    ends_at: Mapped[date | None] = mapped_column(Date)
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id")
    )
    raw_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organization: Mapped["Organization | None"] = relationship(
        back_populates="contracts"
    )
    supplier: Mapped["Company | None"] = relationship(back_populates="contracts")
    source: Mapped["Source | None"] = relationship(back_populates="contracts")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="contract")


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("idx_expenses_date", "expense_date"),
        Index("idx_expenses_person", "person_id"),
        Index("idx_expenses_person_year_date", "person_id", "fiscal_year", "expense_date"),
        Index("idx_expenses_company", "company_id"),
        Index("idx_expenses_org_year", "organization_id", "fiscal_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id")
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id")
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id")
    )
    expense_type: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    commitment_number: Mapped[str | None] = mapped_column(Text)
    liquidation_number: Mapped[str | None] = mapped_column(Text)
    payment_number: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(nullable=False)
    state_code: Mapped[str | None] = mapped_column(String(2))
    municipality_code: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id")
    )
    raw_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organization: Mapped["Organization | None"] = relationship(
        back_populates="expenses"
    )
    person: Mapped["Person | None"] = relationship(back_populates="expenses")
    company: Mapped["Company | None"] = relationship(back_populates="expenses")
    contract: Mapped["Contract | None"] = relationship(back_populates="expenses")
    source: Mapped["Source | None"] = relationship(back_populates="expenses")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    __table_args__ = (
        Index("idx_alerts_entity", "entity_type", "entity_id"),
        Index("idx_alerts_severity_status", "severity", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(Text)
    resource_id: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(Text)
    current_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("idx_users_email", "email", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )
