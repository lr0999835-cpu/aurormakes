"""Idempotent bootstrap for the first tenant/company and super admin user."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import get_connection, init_db


COMPANY_NAME = "Aurora Makes"
COMPANY_SLUG = "aurora-makes"
ADMIN_NAME = "Admin"
ADMIN_EMAIL = "admin@auroramakes.com"
ADMIN_USERNAME = "admin@auroramakes.com"
ADMIN_PASSWORD = "admin123"
ADMIN_ROLE = "super_admin"


def bootstrap_super_admin(reset_password: bool = True) -> dict:
    """Ensure company and super admin exist, are active, and linked together."""
    init_db()

    with get_connection() as conn:
        company = conn.execute(
            "SELECT id FROM companies WHERE slug = ? LIMIT 1",
            (COMPANY_SLUG,),
        ).fetchone()

        if company:
            company_id = int(company["id"])
            conn.execute(
                "UPDATE companies SET name = ?, is_active = 1 WHERE id = ?",
                (COMPANY_NAME, company_id),
            )
        else:
            cursor = conn.execute(
                "INSERT INTO companies (name, slug, is_active) VALUES (?, ?, 1)",
                (COMPANY_NAME, COMPANY_SLUG),
            )
            company_id = int(cursor.lastrowid)

        user = conn.execute(
            "SELECT id FROM users WHERE company_id = ? AND LOWER(email) = LOWER(?) LIMIT 1",
            (company_id, ADMIN_EMAIL),
        ).fetchone()

        password_hash = generate_password_hash(ADMIN_PASSWORD)

        if user:
            user_id = int(user["id"])
            if reset_password:
                conn.execute(
                    """
                    UPDATE users
                    SET username = ?,
                        email = ?,
                        role = ?,
                        is_active = 1,
                        company_id = ?,
                        password_hash = ?
                    WHERE id = ?
                    """,
                    (ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_ROLE, company_id, password_hash, user_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE users
                    SET username = ?,
                        email = ?,
                        role = ?,
                        is_active = 1,
                        company_id = ?
                    WHERE id = ?
                    """,
                    (ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_ROLE, company_id, user_id),
                )
        else:
            cursor = conn.execute(
                """
                INSERT INTO users (company_id, username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (company_id, ADMIN_USERNAME, ADMIN_EMAIL, password_hash, ADMIN_ROLE),
            )
            user_id = int(cursor.lastrowid)

        conn.commit()

    return {
        "company_id": company_id,
        "company_slug": COMPANY_SLUG,
        "user_id": user_id,
        "name": ADMIN_NAME,
        "username": ADMIN_USERNAME,
        "email": ADMIN_EMAIL,
        "role": ADMIN_ROLE,
        "status": "active",
        "password_reset": reset_password,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap company and super admin account")
    parser.add_argument(
        "--no-reset-password",
        action="store_true",
        help="Do not overwrite existing admin password hash when user already exists",
    )
    args = parser.parse_args()

    result = bootstrap_super_admin(reset_password=not args.no_reset_password)
    print("Bootstrap concluído com sucesso:")
    print(f"- company_id: {result['company_id']} ({result['company_slug']})")
    print(f"- user_id: {result['user_id']} ({result['email']})")
    print(f"- role: {result['role']}")
    print(f"- active: {result['status']}")
    print(f"- password_reset: {result['password_reset']}")


if __name__ == "__main__":
    main()
