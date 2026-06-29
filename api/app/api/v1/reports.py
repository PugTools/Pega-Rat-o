import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.db.database import get_db
from app.db.models import RiskAlert
from app.modules.auth.auth_service import get_current_user, require_any_role


router = APIRouter(prefix="/reports", tags=["reports"])
REPORT_EXPORT_ROLES = {"system_admin", "source_admin", "auditor", "compliance_officer"}


def _require_report_exporter(
    current_user: dict = Depends(get_current_user),
) -> dict:
    return require_any_role(current_user, REPORT_EXPORT_ROLES)


@router.get("/alerts.csv")
@log_audit(action="export_alerts_csv", resource_type="risk_alerts")
def export_alerts_csv(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_report_exporter),
) -> StreamingResponse:
    alerts = _query_alerts(db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "severity", "title", "entity_type", "entity_id", "score"])
    for alert in alerts:
        writer.writerow(
            [
                alert.id,
                alert.severity,
                alert.title,
                alert.entity_type,
                alert.entity_id,
                alert.score,
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ongp_alerts.csv"},
    )


@router.get("/alerts.pdf")
@log_audit(action="export_alerts_pdf", resource_type="risk_alerts")
def export_alerts_pdf(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_report_exporter),
) -> StreamingResponse:
    alerts = _query_alerts(db)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "ONGP - Relatorio de Alertas")
    y -= 30
    pdf.setFont("Helvetica", 9)

    for alert in alerts:
        if y < 70:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 9)
        pdf.drawString(40, y, f"{alert.severity.upper()} | {alert.title[:80]}")
        y -= 14
        pdf.drawString(55, y, f"{alert.entity_type}:{alert.entity_id} | Score {alert.score}")
        y -= 18

    pdf.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ongp_alerts.pdf"},
    )


def _query_alerts(db: Session) -> list[RiskAlert]:
    severity_rank = case(
        (RiskAlert.severity == "critical", 1),
        (RiskAlert.severity == "high", 2),
        (RiskAlert.severity == "medium", 3),
        (RiskAlert.severity == "low", 4),
        else_=5,
    )
    return db.query(RiskAlert).order_by(severity_rank, RiskAlert.created_at.desc()).limit(500).all()
