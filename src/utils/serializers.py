from datetime import date, datetime
from decimal import Decimal


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    return value


def to_dict(model) -> dict:
    if model is None:
        return {}

    if isinstance(model, dict):
        return {str(key): _serialize_value(value) for key, value in model.items()}

    if hasattr(model, "__table__"):
        payload = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            payload[column.name] = _serialize_value(value)
        return payload

    raise TypeError(f"Unsupported type for to_dict: {type(model).__name__}")