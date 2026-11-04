import hashlib
import secrets
import hmac
import re
import sqlite3

from file_manager.config import (
    PBKDF2_ITERATIONS,
    SALT_SIZE,
    PBKDF2_MAX_ITERATIONS,
    USERNAME_PATTERN,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    LOGIN_MAX_FAILURES,
    LOGIN_LOCKOUT_MINUTES
)
from file_manager.db import get_connection
from file_manager.audit import log_event, count_recent_failures


def hash_password(password):
    """Хэширует пароль"""
    salt = secrets.token_bytes(SALT_SIZE)
    digest = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt,
        iterations=PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    """Верификация пароля"""
    try:
        algorithm, iterations, salt_hex, hash_hex = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations)
        if iterations < 1 or iterations > PBKDF2_MAX_ITERATIONS:
            return False
        digest = hashlib.pbkdf2_hmac(
            salt=bytes.fromhex(salt_hex),
            password=password.encode("utf-8"),
            iterations=iterations,
            hash_name="sha256"
        )
        return hmac.compare_digest(digest, bytes.fromhex(hash_hex))
    except ValueError:
        return False


def validate_username(username):
    """Валидация логина"""
    if re.fullmatch(USERNAME_PATTERN, username) is None:
        raise ValueError("Логин: 3-32 символа, латинские буквы, цифры, _")


def validate_password(password):
    """Валидация пароля"""
    if not (PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH):
        raise ValueError(f"Длина пароля: {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} символов")


def register_user(username, password):
    """Регистрация пользователя"""
    username = username.lower()
    validate_username(username)
    validate_password(password)
    password_hash = hash_password(password)
    connection = get_connection()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            user_id = cursor.lastrowid
        log_event(event_type="register", user_id=user_id)
        return user_id
    except sqlite3.IntegrityError:
        raise ValueError("Логин занят") from None
    finally:
        connection.close()


DUMMY_HASH = hash_password(secrets.token_hex(16))


def login_user(username, password):
    """Аутентификация"""
    username = username.lower()
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        connection.close()
    safe_name = _safe_username(username)
    user_id = None
    if row is not None:
        user_id, password_hash = row
    if count_recent_failures(details=safe_name, minutes=LOGIN_LOCKOUT_MINUTES) >= LOGIN_MAX_FAILURES:
        log_event(event_type="login_failed", user_id=user_id, details=safe_name)
        raise ValueError("Слишком много неудачных попыток, попробуйте позже")
    if row is None:
        verify_password(password, DUMMY_HASH)
        log_event(event_type="login_failed", details=safe_name)
        return None
    if verify_password(password, password_hash):
        log_event(event_type="login_success", user_id=user_id)
        return user_id
    log_event(event_type="login_failed", user_id=user_id, details=safe_name)
    return None


def _safe_username(username):
    """Логин для журнала: как есть, если подходит белый список, иначе заглушка"""
    if re.fullmatch(USERNAME_PATTERN, username) is None:
        username = "<некорректный логин>"
    return username
