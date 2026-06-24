import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)


PERSON_COLUMNS = (
    "ADD COLUMN IF NOT EXISTS external_id TEXT",
    "ADD COLUMN IF NOT EXISTS party_acronym VARCHAR(16)",
    "ADD COLUMN IF NOT EXISTS state_code VARCHAR(2)",
    "ADD COLUMN IF NOT EXISTS photo_url TEXT",
    "ADD COLUMN IF NOT EXISTS email TEXT",
    "ADD COLUMN IF NOT EXISTS latest_expense_total NUMERIC(18, 2)",
    "ADD COLUMN IF NOT EXISTS latest_expense_year INTEGER",
    "ADD COLUMN IF NOT EXISTS declared_assets_value NUMERIC(18, 2)",
    "ADD COLUMN IF NOT EXISTS declared_assets_year INTEGER",
    "ADD COLUMN IF NOT EXISTS salary_reference_value NUMERIC(18, 2)",
    "ADD COLUMN IF NOT EXISTS salary_reference_year INTEGER",
    "ADD COLUMN IF NOT EXISTS salary_reference_source TEXT",
    "ADD COLUMN IF NOT EXISTS asset_salary_ratio NUMERIC(18, 4)",
)

INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_persons_origin_external ON persons (data_origin, external_id)",
    "CREATE INDEX IF NOT EXISTS idx_persons_party_state ON persons (party_acronym, state_code)",
    "CREATE INDEX IF NOT EXISTS idx_persons_expense_total ON persons (latest_expense_total)",
    "CREATE INDEX IF NOT EXISTS idx_persons_asset_salary_ratio ON persons (asset_salary_ratio DESC)",
    "CREATE INDEX IF NOT EXISTS idx_persons_declared_assets ON persons (declared_assets_value DESC)",
    "CREATE INDEX IF NOT EXISTS idx_persons_state_party_expense ON persons (state_code, party_acronym, latest_expense_total DESC)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_person_year_date ON expenses (person_id, fiscal_year, expense_date)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_person_commitment ON expenses (person_id, commitment_number)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_state_year_amount ON expenses (state_code, fiscal_year, amount DESC)",
    "CREATE INDEX IF NOT EXISTS idx_contracts_status_value ON contracts (status, total_value DESC)",
)


def ensure_postgres_runtime_schema(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    try:
        with engine.begin() as connection:
            for column_statement in PERSON_COLUMNS:
                connection.execute(text(f"ALTER TABLE persons {column_statement}"))
            for index_statement in INDEX_STATEMENTS:
                connection.execute(text(index_statement))
    except SQLAlchemyError:
        logger.exception("postgres_runtime_schema_maintenance_failed")
