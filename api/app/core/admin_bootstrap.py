from __future__ import annotations

import json

from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import User
from app.modules.auth.auth_service import ensure_bootstrap_admin, ensure_system_roles


def main() -> None:
    email = settings.ADMIN_BOOTSTRAP_EMAIL.strip().lower()
    with SessionLocal() as db:
        ensure_system_roles(db)
        ensure_bootstrap_admin(db)

        user = None
        if email:
            user = (
                db.query(User)
                .options(selectinload(User.roles))
                .filter(User.email == email)
                .one_or_none()
            )

        payload = {
            "admin_bootstrap_email_configured": bool(email),
            "admin_bootstrap_password_configured": bool(
                settings.ADMIN_BOOTSTRAP_PASSWORD.strip()
            ),
            "admin_bootstrap_reset_password": settings.ADMIN_BOOTSTRAP_RESET_PASSWORD,
            "user_exists": user is not None,
            "user_email": user.email if user else email or None,
            "user_active": user.active if user else None,
            "user_roles": sorted(role.name for role in user.roles) if user else [],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
