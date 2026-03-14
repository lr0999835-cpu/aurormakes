from functools import wraps

from flask import abort, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from database import get_connection

ROLE_PERMISSIONS = {
    "viewer": {"orders:read", "products:read", "stock:read", "channels:read"},
    "operator": {
        "orders:read",
        "orders:write",
        "products:read",
        "products:write",
        "stock:read",
        "stock:write",
        "channels:read",
    },
    "company_admin": {
        "dashboard:read",
        "orders:read",
        "orders:write",
        "products:read",
        "products:write",
        "stock:read",
        "stock:write",
        "channels:read",
        "channels:write",
        "integrations:read",
        "users:read",
        "users:write",
    },
    "super_admin": {"*"},
}


def permissions_for_role(role):
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user, permission):
    if not user:
        return False
    perms = permissions_for_role(user["role"])
    return "*" in perms or permission in perms


def authenticate_user(company_slug, login, password):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.company_id, u.username, u.email, u.password_hash, u.role, u.is_active,
                   c.slug as company_slug, c.name as company_name, c.is_active as company_active
            FROM users u
            JOIN companies c ON c.id = u.company_id
            WHERE c.slug = ?
              AND (LOWER(u.email) = LOWER(?) OR LOWER(u.username) = LOWER(?))
            LIMIT 1
            """,
            (company_slug.strip().lower(), login.strip(), login.strip()),
        ).fetchone()

    if not row:
        return None, "Credenciais inválidas"
    if int(row["company_active"]) != 1:
        return None, "Empresa inativa"
    if int(row["is_active"]) != 1:
        return None, "Usuário inativo"
    if not check_password_hash(row["password_hash"], password):
        return None, "Credenciais inválidas"

    user = {
        "id": int(row["id"]),
        "company_id": int(row["company_id"]),
        "company_slug": row["company_slug"],
        "company_name": row["company_name"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
    }
    return user, None


def load_current_user():
    auth_user = session.get("auth_user")
    g.current_user = auth_user
    return auth_user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = load_current_user()
        if not user:
            return redirect(url_for("admin.admin_login", next=request.full_path if request.query_string else request.path))
        return view(*args, **kwargs)

    return wrapped


def permission_required(permission):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = load_current_user()
            if not user:
                return redirect(url_for("admin.admin_login", next=request.full_path if request.query_string else request.path))
            if not has_permission(user, permission):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def api_auth_required(permission=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = load_current_user()
            if not user:
                return {"error": "Não autenticado"}, 401
            if permission and not has_permission(user, permission):
                return {"error": "Sem permissão"}, 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def tenant_for_request(default_slug="aurora-makes"):
    user = load_current_user()
    if user:
        return user["company_id"]

    slug = (
        request.headers.get("X-Company")
        or request.args.get("company")
        or ((request.get_json(silent=True) or {}).get("company") if request.method in {"POST", "PUT", "PATCH"} else None)
        or default_slug
    )
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM companies WHERE slug = ? AND is_active = 1", (slug.strip().lower(),)).fetchone()
    return int(row["id"]) if row else None
