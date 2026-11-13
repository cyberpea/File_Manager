import json

from file_manager.files import read_file
from file_manager.audit import log_event
from file_manager.config import JSON_MAX_DEPTH


def read_json(user_id, filename):
    """Читает файл пользователя и разбирает его как JSON"""
    data = read_file(user_id, filename)
    try:
        text = data.decode("utf-8")
        result = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise ValueError("Файл не является корректным JSON") from None
    except RecursionError:
        log_event("limit_exceeded", user_id, repr(filename))
        raise ValueError("Слишком глубокая вложенность") from None
    if _is_too_deep(result):
        log_event("limit_exceeded", user_id, repr(filename))
        raise ValueError("Слишком глубокая вложенность")
    return result


def _is_too_deep(obj):
    """Проверяет без рекурсии, превышает ли вложенность JSON_MAX_DEPTH"""
    todo = [(obj, 1)]
    while todo:
        current, depth = todo.pop()
        if depth > JSON_MAX_DEPTH:
            return True
        if isinstance(current, dict):
            children = current.values()
        elif isinstance(current, list):
            children = current
        else:
            continue
        for child in children:
            todo.append((child, depth + 1))
    return False


def _reject_constant(name):
    """Запрещает NaN и Infinity: их нет в стандарте JSON"""
    raise ValueError("Некорректные данные в файле")
