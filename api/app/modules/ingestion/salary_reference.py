from decimal import Decimal


SALARY_REFERENCE_YEAR = 2026
SALARY_REFERENCE_SOURCE = "referencia-subsidio-publico-ongp-2026"

MONTHLY_SALARY_BY_ROLE = {
    "Presidente": Decimal("46366.19"),
    "Vice-presidente": Decimal("46366.19"),
    "Ministro": Decimal("46366.19"),
    "Governador": Decimal("35000.00"),
    "Vice-governador": Decimal("25000.00"),
    "Senador": Decimal("46366.19"),
    "Deputado Federal": Decimal("46366.19"),
    "Deputado Estadual": Decimal("34000.00"),
    "Deputado Distrital": Decimal("34000.00"),
    "Prefeito": Decimal("25000.00"),
    "Vice-prefeito": Decimal("15000.00"),
    "Vereador": Decimal("12000.00"),
    "Secretario": Decimal("25000.00"),
    "Assessor": Decimal("8000.00"),
}


def monthly_salary_for_role(role_name: str | None) -> Decimal | None:
    if not role_name:
        return None
    return MONTHLY_SALARY_BY_ROLE.get(role_name)


def annual_salary_for_role(role_name: str | None) -> Decimal | None:
    monthly_salary = monthly_salary_for_role(role_name)
    if monthly_salary is None:
        return None
    return monthly_salary * Decimal("12")


def asset_salary_ratio(
    declared_assets_value: Decimal | None,
    role_name: str | None,
) -> Decimal | None:
    annual_salary = annual_salary_for_role(role_name)
    if declared_assets_value is None or annual_salary is None or annual_salary <= 0:
        return None
    return (declared_assets_value / annual_salary).quantize(Decimal("0.0001"))
