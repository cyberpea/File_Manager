import pytest

from file_manager import db
from file_manager.audit import log_event, count_recent_failures, list_events, list_operations
from file_manager.config import AUDIT_DETAILS_MAX_LENGTH
from file_manager.files import create_file


def test_unknown_event_type_is_rejected(sandbox, events):
    with pytest.raises(ValueError):
        log_event("something_else")
    assert events() == []


def test_details_are_truncated(sandbox, events):
    log_event("access_denied", details="x" * (AUDIT_DETAILS_MAX_LENGTH + 100))
    assert len(events()[0][1]) == AUDIT_DETAILS_MAX_LENGTH


def test_sql_in_details_is_stored_as_text(sandbox, events):
    payload = "x'); DROP TABLE users; --"
    log_event("access_denied", details=payload)
    assert events() == [("access_denied", payload)]
    connection = db.get_connection()
    try:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    finally:
        connection.close()


def test_failures_are_counted_per_login(sandbox):
    log_event("login_failed", details="alice")
    log_event("login_failed", details="alice")
    log_event("login_failed", details="bob")
    log_event("login_success", details="alice")
    assert count_recent_failures("alice", 15) == 2
    assert count_recent_failures("bob", 15) == 1
    assert count_recent_failures("carol", 15) == 0


def test_old_failures_are_not_counted(sandbox):
    connection = db.get_connection()
    try:
        with connection:
            connection.execute(
                "INSERT INTO audit_log (timestamp, event_type, details) VALUES (datetime('now', '-16 minutes'), ?, ?)",
                ("login_failed", "alice"),
            )
    finally:
        connection.close()
    assert count_recent_failures("alice", 15) == 0
    assert count_recent_failures("alice", 20) == 1


def test_user_sees_only_own_events(user_id, other_id):
    log_event("access_denied", user_id, "mine")
    log_event("access_denied", other_id, "theirs")
    log_event("login_failed", None, "alice")
    assert [row[2] for row in list_events(user_id, 30)] == ["mine"]
    assert [row[2] for row in list_events(other_id, 30)] == ["theirs"]


def test_user_sees_only_own_operations(user_id, other_id):
    create_file(user_id, "mine.txt", b"1")
    create_file(other_id, "theirs.txt", b"2")
    assert [row[2] for row in list_operations(user_id, 30)] == [f"{user_id}/mine.txt"]


def test_history_is_limited_and_newest_first(user_id):
    for number in range(5):
        log_event("access_denied", user_id, str(number))
    assert [row[2] for row in list_events(user_id, 3)] == ["4", "3", "2"]


def test_foreign_keys_are_enforced(sandbox):
    connection = db.get_connection()
    try:
        with pytest.raises(db.sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO files (filename, size, location, owner_id) VALUES (?, ?, ?, ?)",
                ("a.txt", 1, "999/a.txt", 999),
            )
    finally:
        connection.close()


def test_invalid_operation_type_is_rejected_by_schema(user_id):
    connection = db.get_connection()
    try:
        with pytest.raises(db.sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO operations (operation_type, user_id, file_path) VALUES (?, ?, ?)",
                ("hack", user_id, "x"),
            )
    finally:
        connection.close()
