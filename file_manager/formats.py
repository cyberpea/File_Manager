import json
from defusedxml import ElementTree as DET, DefusedXmlException

from file_manager.files import read_file, modify_file, create_file
from file_manager.audit import log_event
from file_manager.config import JSON_MAX_DEPTH, XML_MAX_DEPTH


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


def write_json(user_id, filename, obj, overwrite=False):
    """Сохраняет объект Python как JSON-файл пользователя"""
    if _is_too_deep(obj):
        log_event("limit_exceeded", user_id, repr(filename))
        raise ValueError("Слишком глубокая вложенность")
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)
        data = text.encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("Данные нельзя сохранить как JSON") from None
    if overwrite:
        return modify_file(user_id, filename, data)
    return create_file(user_id, filename, data)


def read_xml(user_id, filename):
    """Читает файл пользователя и разбирает его как XML, возвращает корневой элемент"""
    data = read_file(user_id, filename)
    try:
        root = DET.fromstring(data, forbid_dtd=True)
    except DefusedXmlException:
        log_event("access_denied", user_id, repr(filename))
        raise ValueError("Файл содержит запрещенные конструкции XML") from None
    except (DET.ParseError, LookupError):
        raise ValueError("Файл не является корректным XML") from None
    if _xml_too_deep(root):
        log_event("limit_exceeded", user_id, repr(filename))
        raise ValueError("Слишком глубокая вложенность")
    return root


def _xml_too_deep(root):
    """Проверяет без рекурсии, превышает ли вложенность XML_MAX_DEPTH"""
    todo = [(root, 1)]
    while todo:
        current, depth = todo.pop()
        if depth > XML_MAX_DEPTH:
            return True
        for child in current:
            todo.append((child, depth + 1))
    return False
