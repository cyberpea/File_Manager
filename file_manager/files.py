import os

from file_manager.config import STORAGE_DIR, MAX_FILE_SIZE
from file_manager.audit import log_event


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