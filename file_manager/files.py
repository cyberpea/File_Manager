from file_manager.config import STORAGE_DIR
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