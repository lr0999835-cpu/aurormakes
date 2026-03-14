from datetime import datetime
from zoneinfo import ZoneInfo

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def now_brt():
    return datetime.now(BRAZIL_TZ)


def to_brt(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(BRAZIL_TZ)


def format_brl(value):
    amount = float(value or 0)
    formatted = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def format_date_br(value):
    if not value:
        return "-"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return to_brt(value).strftime("%d/%m/%Y")


def format_time_br(value):
    if not value:
        return "-"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return to_brt(value).strftime("%H:%M")


def format_datetime_br(value):
    if not value:
        return "-"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return to_brt(value).strftime("%d/%m/%Y %H:%M")
