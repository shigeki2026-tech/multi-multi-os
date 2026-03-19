from datetime import date, datetime
from decimal import Decimal


def to_dict(model) -> dict:
    payload = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            payload[column.name] = value.isoformat(sep=" ", timespec="seconds")
        elif isinstance(value, date):
            payload[column.name] = value.isoformat()
        elif isinstance(value, Decimal):
            payload[column.name] = float(value)
        else:
            payload[column.name] = value
    return payload
