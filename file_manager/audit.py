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


def count_recent_failures(details, minutes):
    """Считает login_failed с данным details за последние minutes минут"""
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            SELECT COUNT(*) FROM audit_log
            WHERE event_type = ? AND details = ? AND timestamp >= datetime('now', ?)
            """,
            ("login_failed", details, f"-{minutes} minutes"),
        )
        return cursor.fetchone()[0]
    finally:
        connection.close()


def log_operations(connection, operation_type, file_id, user_id, file_path):
    """Записывает операцию с файлом в operations (в транзакции вызывающего)"""
    connection.execute(
        "INSERT INTO operations (operation_type, file_id, user_id, file_path) VALUES (?, ?, ?, ?)",
        (operation_type, file_id, user_id, file_path),
    )
