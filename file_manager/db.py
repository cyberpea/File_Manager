import sqlite3
from file_manager.config import DB_PATH


def get_connection():
    """Подключает БД"""
    connection = sqlite3.connect(DB_PATH)
    connection.execute('PRAGMA foreign_keys = ON') # Проверка внешних ключей
    return connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    size INTEGER NOT NULL CHECK (size >= 0),
    location TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('create', 'modify', 'delete')),
    file_id INTEGER,
    user_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL CHECK (event_type IN (
    'register', 'login_success', 'login_failed',
    'access_denied', 'limit_exceeded'
    )),
    user_id INTEGER,
    details TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""


def init_db():
    """Инициализация БД"""
    connection = get_connection()
    # executescript используем только для SCHEMA: это неизменяемый текст из нашего же кода.
    # Всё, где есть данные извне, выполняется через execute с ?
    try:
        connection.executescript(SCHEMA)
    finally:
        connection.close()
