import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_phone(value):
    return "".join(char for char in (value or "") if char.isdigit())


def _validate_customer_payload(payload, require_password=True):
    data = {
        "nome_completo": (payload.get("nome_completo") or payload.get("nomeCompleto") or "").strip(),
        "email": (payload.get("email") or "").strip().lower(),
        "telefone": _normalize_phone(payload.get("telefone") or payload.get("phone") or ""),
        "cpf": (payload.get("cpf") or "").strip(),
        "data_nascimento": (payload.get("data_nascimento") or payload.get("dataNascimento") or "").strip(),
        "genero": (payload.get("genero") or "").strip(),
        "aceita_marketing": 1 if payload.get("aceita_marketing") or payload.get("aceitaMarketing") else 0,
        "senha": payload.get("senha") or "",
        "confirmar_senha": payload.get("confirmar_senha") or payload.get("confirmarSenha") or "",
    }

    if not data["nome_completo"]:
        raise ValueError("Informe seu nome completo.")
    if not data["email"] or not EMAIL_RE.match(data["email"]):
        raise ValueError("Informe um e-mail válido.")
    if not data["telefone"]:
        raise ValueError("Informe seu telefone.")
    if require_password:
        if len(data["senha"]) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres.")
        if data["senha"] != data["confirmar_senha"]:
            raise ValueError("A confirmação da senha não confere.")
    return data


def create_customer(company_id, payload):
    data = _validate_customer_payload(payload, require_password=True)
    password_hash = generate_password_hash(data["senha"])

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM customers WHERE company_id = ? AND LOWER(email) = LOWER(?) LIMIT 1",
            (int(company_id), data["email"]),
        ).fetchone()
        if existing:
            raise ValueError("Já existe uma conta com este e-mail.")

        cursor = conn.execute(
            """
            INSERT INTO customers (
                company_id, nome_completo, email, telefone, senha_hash, cpf,
                data_nascimento, genero, ativo, aceita_marketing
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                int(company_id),
                data["nome_completo"],
                data["email"],
                data["telefone"],
                password_hash,
                data["cpf"],
                data["data_nascimento"] or None,
                data["genero"],
                int(data["aceita_marketing"]),
            ),
        )
        conn.commit()

    return get_customer_by_id(company_id, int(cursor.lastrowid))


def authenticate_customer(company_id, email, senha):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, company_id, nome_completo, email, telefone, senha_hash, cpf,
                   data_nascimento, genero, ativo, aceita_marketing
            FROM customers
            WHERE company_id = ? AND LOWER(email) = LOWER(?)
            LIMIT 1
            """,
            (int(company_id), (email or "").strip().lower()),
        ).fetchone()

    if not row or int(row["ativo"]) != 1 or not check_password_hash(row["senha_hash"], senha or ""):
        return None
    return _serialize_customer(row)


def get_customer_by_id(company_id, customer_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, company_id, nome_completo, email, telefone, cpf,
                   data_nascimento, genero, ativo, aceita_marketing, created_at, updated_at
            FROM customers WHERE company_id = ? AND id = ? LIMIT 1
            """,
            (int(company_id), int(customer_id)),
        ).fetchone()
    return _serialize_customer(row) if row else None


def update_customer_profile(company_id, customer_id, payload):
    data = _validate_customer_payload(payload, require_password=False)

    with get_connection() as conn:
        conflict = conn.execute(
            "SELECT id FROM customers WHERE company_id = ? AND LOWER(email) = LOWER(?) AND id <> ? LIMIT 1",
            (int(company_id), data["email"], int(customer_id)),
        ).fetchone()
        if conflict:
            raise ValueError("Este e-mail já está em uso por outra conta.")

        conn.execute(
            """
            UPDATE customers
            SET nome_completo = ?,
                email = ?,
                telefone = ?,
                cpf = ?,
                data_nascimento = ?,
                genero = ?,
                aceita_marketing = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE company_id = ? AND id = ?
            """,
            (
                data["nome_completo"],
                data["email"],
                data["telefone"],
                data["cpf"],
                data["data_nascimento"] or None,
                data["genero"],
                int(data["aceita_marketing"]),
                int(company_id),
                int(customer_id),
            ),
        )
        conn.commit()

    return get_customer_by_id(company_id, customer_id)


def list_customer_addresses(company_id, customer_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM customer_addresses WHERE company_id = ? AND customer_id = ? ORDER BY is_default DESC, id DESC",
            (int(company_id), int(customer_id)),
        ).fetchall()
    return [_serialize_address(row) for row in rows]


def create_customer_address(company_id, customer_id, payload):
    data = _validate_address(payload)
    with get_connection() as conn:
        if data["is_default"]:
            conn.execute(
                "UPDATE customer_addresses SET is_default = 0 WHERE company_id = ? AND customer_id = ?",
                (int(company_id), int(customer_id)),
            )
        cursor = conn.execute(
            """
            INSERT INTO customer_addresses (
                company_id, customer_id, cep, endereco, numero, complemento,
                bairro, cidade, estado, referencia, is_default
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(company_id), int(customer_id), data["cep"], data["endereco"], data["numero"],
                data["complemento"], data["bairro"], data["cidade"], data["estado"], data["referencia"], int(data["is_default"]),
            ),
        )
        conn.commit()
        address_id = int(cursor.lastrowid)

        row = conn.execute(
            "SELECT * FROM customer_addresses WHERE company_id = ? AND customer_id = ? AND id = ?",
            (int(company_id), int(customer_id), address_id),
        ).fetchone()
    return _serialize_address(row)


def _validate_address(payload):
    data = {
        "cep": (payload.get("cep") or "").strip(),
        "endereco": (payload.get("endereco") or "").strip(),
        "numero": (payload.get("numero") or "").strip(),
        "complemento": (payload.get("complemento") or "").strip(),
        "bairro": (payload.get("bairro") or "").strip(),
        "cidade": (payload.get("cidade") or "").strip(),
        "estado": (payload.get("estado") or "").strip(),
        "referencia": (payload.get("referencia") or "").strip(),
        "is_default": bool(payload.get("is_default") or payload.get("isDefault")),
    }
    for field in ["cep", "endereco", "numero", "bairro", "cidade", "estado"]:
        if not data[field]:
            raise ValueError(f"Campo obrigatório: {field}.")
    return data


def _serialize_customer(row):
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "company_id": int(row["company_id"]),
        "nome_completo": row["nome_completo"],
        "email": row["email"],
        "telefone": row["telefone"] or "",
        "cpf": row["cpf"] or "",
        "data_nascimento": row["data_nascimento"] or "",
        "genero": row["genero"] or "",
        "aceita_marketing": bool(row["aceita_marketing"]),
        "ativo": bool(row["ativo"]),
    }


def _serialize_address(row):
    return {
        "id": int(row["id"]),
        "cep": row["cep"],
        "endereco": row["endereco"],
        "numero": row["numero"],
        "complemento": row["complemento"] or "",
        "bairro": row["bairro"],
        "cidade": row["cidade"],
        "estado": row["estado"],
        "referencia": row["referencia"] or "",
        "is_default": bool(row["is_default"]),
    }
