import pytest

from file_manager import db
from file_manager.auth import register_user, login_user
from file_manager.config import LOGIN_MAX_FAILURES


def test_register_then_login_returns_same_id(sandbox):
    registered_id = register_user("viki", "password123")
    assert login_user("viki", "password123") == registered_id


def test_wrong_password_is_rejected(sandbox):
    register_user("viki", "password123")
    assert login_user("viki", "password124") is None


def test_unknown_user_is_rejected(sandbox):
    assert login_user("nobody", "password123") is None


def test_duplicate_username_is_rejected(sandbox):
    register_user("viki", "password123")
    with pytest.raises(ValueError):
        register_user("viki", "another_password")


def test_username_is_case_insensitive(sandbox):
    registered_id = register_user("Viki", "password123")
    assert login_user("VIKI", "password123") == registered_id
    with pytest.raises(ValueError):
        register_user("vIkI", "password123")


def test_password_is_not_stored_in_plain_text(sandbox):
    register_user("viki", "password123")
    connection = db.get_connection()
    try:
        stored = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    finally:
        connection.close()
    assert "password123" not in stored
    assert stored.startswith("pbkdf2_sha256$")


def test_sql_injection_in_login_does_not_work(sandbox):
    register_user("viki", "password123")
    assert login_user("' OR '1'='1", "x") is None
    assert login_user("viki' --", "x") is None
    assert login_user("viki", "password123") is not None


def test_login_events_are_logged(sandbox, events):
    register_user("viki", "password123")
    login_user("viki", "wrong_password")
    login_user("viki", "password123")
    assert events() == [
        ("register", None),
        ("login_failed", "viki"),
        ("login_success", None),
    ]


def test_bad_username_is_not_written_to_log(sandbox, events):
    login_user("admin\n2026-01-01 login_success", "x")
    assert events() == [("login_failed", "<некорректный логин>")]


def test_account_is_locked_after_too_many_failures(sandbox):
    register_user("viki", "password123")
    for attempt in range(LOGIN_MAX_FAILURES):
        assert login_user("viki", "wrong_password") is None
    with pytest.raises(ValueError):
        login_user("viki", "password123")


def test_lockout_is_the_same_for_unknown_user(sandbox):
    for attempt in range(LOGIN_MAX_FAILURES):
        assert login_user("nobody", "wrong_password") is None
    with pytest.raises(ValueError):
        login_user("nobody", "wrong_password")
