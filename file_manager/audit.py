from file_manager.config import AUDIT_DETAILS_MAX_LENGTH, AUDIT_EVENT_TYPES
from file_manager.db import get_connection


def log_event(event_type, user_id=None, details=None):
    """Записывает событие безопасности в audit_log"""
    if event_type not in AUDIT_EVENT_TYPES:
        raise ValueError(f"{event_type} не является доступным значением")
    if details is not None:
        details = details[:AUDIT_DETAILS_MAX_LENGTH]
    connection = get_connection()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO audit_log (event_type, user_id, details) VALUES (?, ?, ?)",
                (event_type, user_id, details),
            )
        return cursor.lastrowid
    finally:
        connection.close()