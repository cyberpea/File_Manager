import os
import re

from file_manager.config import STORAGE_DIR, MAX_FILE_SIZE, FILENAME_PATTERN
from file_manager.audit import log_event, log_operations
from file_manager.db import get_connection


def resolve_safe_path(user_id, user_path):
    """Возвращает абсолютный путь внутри папки пользователя или бросает ValueError"""
    user_dir = (STORAGE_DIR / str(user_id)).resolve()
    target = (user_dir / user_path).resolve()
    if not target.is_relative_to(user_dir):
        log_event("access_denied", user_id, repr(user_path))
        raise ValueError("Доступ запрещен: путь выходит за пределы вашей папки")
    if target == user_dir:
        log_event("access_denied", user_id, repr(user_path))
        raise ValueError("Укажите имя файла")
    return target


def read_file(user_id, user_path):
    """Возвращает содержимое файла (bytes) или бросает ValueError"""
    path = resolve_safe_path(user_id, user_path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as f:
            data = f.read(MAX_FILE_SIZE + 1)
    except FileNotFoundError:
        raise ValueError("Файла не существует") from None
    except OSError:
        raise ValueError("Не удалось прочитать файл") from None
    if len(data) > MAX_FILE_SIZE:
        log_event("limit_exceeded", user_id, repr(user_path))
        raise ValueError("Файл слишком большой")
    return data


def validate_filename(filename):
    """Валидация имени файла"""
    if re.fullmatch(FILENAME_PATTERN, filename) is None:
        raise ValueError("Имя файла: 1-100 символов, буквы, цифры, _, дефис, точка и пробел")


def create_file(user_id, filename, data):
    """Создает новый файл в папке пользователя или бросает ValueError"""
    validate_filename(filename)
    if len(data) > MAX_FILE_SIZE:
        log_event("limit_exceeded", user_id, repr(filename))
        raise ValueError("Размер файла превышает лимит")
    path = resolve_safe_path(user_id, filename)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    location = f"{user_id}/{filename}"
    connection = get_connection()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO files (filename, size, location, owner_id) VALUES (?, ?, ?, ?)",
                (filename, len(data), location, user_id),
            )
            log_operations(connection, "create", cursor.lastrowid, user_id, location)
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
            except FileExistsError:
                raise ValueError("Файл с таким именем уже существует") from None
            except OSError:
                raise ValueError("Не удалось создать файл") from None
    finally:
        connection.close()
    return path


def modify_file(user_id, filename, data):
    """Изменяет существующий файл в папке пользователя или бросает ValueError"""
    validate_filename(filename)
    if len(data) > MAX_FILE_SIZE:
        log_event("limit_exceeded", user_id, repr(filename))
        raise ValueError("Размер файла превышает лимит")
    path = resolve_safe_path(user_id, filename)
    location = f"{user_id}/{filename}"
    connection = get_connection()
    try:
        with connection:
            row = connection.execute(
                "SELECT id FROM files WHERE owner_id = ? AND filename = ?",
                (user_id, filename),
            ).fetchone()
            if row is None:
                raise ValueError("Файла с таким именем не существует")
            file_id = row[0]
            connection.execute(
                "UPDATE files SET size = ? WHERE id = ?",
                (len(data), file_id),
            )
            log_operations(connection, "modify", file_id, user_id, location)
            try:
                fd = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
            except OSError:
                raise ValueError("Не удалось изменить файл") from None
    finally:
        connection.close()
    return path
