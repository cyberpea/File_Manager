import pytest

from file_manager import db, files


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Временная БД и временное хранилище для одного теста"""
    storage = tmp_path / "storage"
    storage.mkdir()
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(files, "STORAGE_DIR", storage)
    db.init_db()
    return storage


def _add_user(username):
    connection = db.get_connection()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, "x"),
            )
        return cursor.lastrowid
    finally:
        connection.close()


@pytest.fixture
def user_id(sandbox):
    """Пользователь в тестовой БД (без настоящего пароля, чтобы тесты были быстрыми)"""
    return _add_user("alice")


@pytest.fixture
def other_id(sandbox):
    """Второй пользователь для проверок изоляции"""
    return _add_user("bob")


@pytest.fixture
def events(sandbox):
    """Функция, возвращающая записи audit_log как список пар (event_type, details)"""
    def fetch():
        connection = db.get_connection()
        try:
            return connection.execute(
                "SELECT event_type, details FROM audit_log ORDER BY id"
            ).fetchall()
        finally:
            connection.close()
    return fetch


@pytest.fixture
def operations(sandbox):
    """Функция, возвращающая записи operations как список троек (operation_type, file_id, file_path)"""
    def fetch():
        connection = db.get_connection()
        try:
            return connection.execute(
                "SELECT operation_type, file_id, file_path FROM operations ORDER BY id"
            ).fetchall()
        finally:
            connection.close()
    return fetch
