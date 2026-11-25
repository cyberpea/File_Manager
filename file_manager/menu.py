import getpass
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from file_manager import archives
from file_manager import audit
from file_manager import auth
from file_manager import disks
from file_manager import files
from file_manager import formats
from file_manager.config import HISTORY_LIMIT


def auth_menu():
    """Экран входа. Возвращает user_id после успешного входа или None, если выбран выход"""
    while True:
        print()
        print("1. Войти")
        print("2. Зарегистрироваться")
        print("0. Выход")
        choice = input("> ").strip()

        if choice == "1":
            login = input("Логин: ")
            password = getpass.getpass("Пароль: ")
            try:
                user_id = auth.login_user(login, password)
                if user_id is None:
                    print("Неверный логин или пароль")
                else:
                    return user_id
            except ValueError as error:
                print(error)
        elif choice == "2":
            login = input("Логин: ")
            password = getpass.getpass("Пароль: ")
            try:
                auth.register_user(login, password)
                print("Успешная регистрация, теперь вы можете войти")
            except ValueError as error:
                print(error)
        elif choice == "0":
            return None
        else:
            print("Нет такого пункта")


def main_menu(user_id):
    """Главное меню. Возвращается, когда пользователь выходит из аккаунта"""
    while True:
        print()
        print("1. Диски")
        print("2. Прочитать файл")
        print("3. Показать файлы")
        print("4. Создать файл")
        print("5. Редактировать файл")
        print("6. Удалить файл")
        print("7. Прочитать JSON")
        print("8. Записать JSON")
        print("9. Прочитать XML")
        print("10. Записать XML")
        print("11. Создать ZIP-архив")
        print("12. Распаковать ZIP-архив")
        print("13. История операций с файлами")
        print("14. Журнал событий безопасности")
        print("0. Выйти из аккаунта")
        choice = input("> ").strip()

        if choice == "1":
            show_disks()
        elif choice == "2":
            show_file(user_id)
        elif choice == "3":
            show_files(user_id)
        elif choice == "4":
            create_file_menu(user_id)
        elif choice == "5":
            modify_file_menu(user_id)
        elif choice == "6":
            delete_file_menu(user_id)
        elif choice == "7":
            show_json(user_id)
        elif choice == "8":
            write_json_menu(user_id)
        elif choice == "9":
            show_xml(user_id)
        elif choice == "10":
            write_xml_menu(user_id)
        elif choice == "11":
            create_zip_menu(user_id)
        elif choice == "12":
            extract_zip_menu(user_id)
        elif choice == "13":
            show_operations(user_id)
        elif choice == "14":
            show_events(user_id)
        elif choice == "0":
            audit.log_event("logout", user_id)
            return
        else:
            print("Нет такого пункта")


def show_disks():
    for disk in disks.get_disks():
        print()
        print("Устройство:", disk["device"])
        print("Точка монтирования:", disk["mountpoint"])
        print("Файловая система:", disk["fstype"])
        print("Хранилище:")
        print(f"\t-Использовано: {disk["used"] / 1024**3:.1f} ГБ")
        print(f"\t-Свободно: {disk["free"] / 1024**3:.1f} ГБ")
        print(f"\t-Всего: {disk["total"] / 1024**3:.1f} ГБ")


def show_file(user_id):
    filename = input("Имя файла: ")
    try:
        data = files.read_file(user_id, filename)
    except ValueError as error:
        print(error)
        return
    print(_safe_text(data))


def _safe_text(data):
    """Байты из файла -> строка, которую безопасно печатать в терминал"""
    text = data.decode("utf-8", errors="replace")
    return _clean(text)


def _clean(text):
    """Заменяет на ? всё, кроме печатных символов, переноса строки и табуляции.
    Защита от управляющих последовательностей терминала во внешних данных"""
    result = ""
    for ch in text:
        if ch.isprintable() or ch in ["\n", "\t"]:
            result += ch
        else:
            result += "?"
    return result


def show_files(user_id):
    rows = files.list_files(user_id)
    if not rows:
        print("Файлов нет")
    else:
        for filename, size, created_at in rows:
            print(f"{filename}: {size} байт, создан {_local_time(created_at)}")


def create_file_menu(user_id):
    filename = input("Введите имя файла: ")
    data = input("Введите содержимое файла одной строкой:\n")
    try:
        files.create_file(user_id, filename, data.encode("utf-8"))
        print("Файл создан")
    except ValueError as error:
        print(error)


def modify_file_menu(user_id):
    filename = input("Введите имя файла: ")
    data = input("Введите новое содержимое файла одной строкой:\n")
    try:
        files.modify_file(user_id, filename, data.encode("utf-8"))
        print("Файл изменен")
    except ValueError as error:
        print(error)


def delete_file_menu(user_id):
    filename = input("Введите имя файла: ")
    while True:
        choice = input("Удалить файл? (да/нет): ")
        if choice == "да":
            try:
                files.delete_file(user_id, filename)
                print("Файл удален")
                return
            except ValueError as error:
                print(error)
                return
        elif choice == "нет":
            print("Удаление файла отменено")
            return
        else:
            print("Введите 'да' или 'нет'")


def _local_time(timestamp):
    """Время из БД (UTC, 'ГГГГ-ММ-ДД ЧЧ:ММ:СС') -> строка в местном времени"""
    moment = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    moment = moment.replace(tzinfo=timezone.utc).astimezone()
    return moment.strftime("%d.%m.%Y %H:%M:%S")


def show_json(user_id):
    filename = input("Имя файла: ")
    try:
        obj = formats.read_json(user_id, filename)
    except ValueError as error:
        print(error)
        return
    print(_clean(json.dumps(obj, ensure_ascii=False, indent=2)))


def write_json_menu(user_id):
    filename = input("Введите имя файла: ")
    text = input("Введите JSON одной строкой:\n")
    try:
        obj = json.loads(text)
    except ValueError:
        print("Это не JSON")
        return
    try:
        formats.write_json(user_id, filename, obj)
        print("Файл создан")
    except ValueError as error:
        print(error)


def show_xml(user_id):
    filename = input("Имя файла: ")
    try:
        root = formats.read_xml(user_id, filename)
    except ValueError as error:
        print(error)
        return
    todo = [(root, 0)]
    while todo:
        element, depth = todo.pop()
        line = "  " * depth + f"<{element.tag}>"
        for name in element.attrib:
            line += f" {name}={element.attrib[name]!r}"
        if element.text is not None and element.text.strip():
            line += ": " + element.text.strip()
        print(_clean(line))
        for child in reversed(element):
            todo.append((child, depth + 1))


def write_xml_menu(user_id):
    filename = input("Введите имя файла: ")
    root = ET.Element(input("Имя корневого элемента: "))
    print("Вложенные элементы. Пустое имя - закончить")
    while True:
        tag = input("Имя элемента: ")
        if tag == "":
            break
        child = ET.SubElement(root, tag)
        child.text = input("Текст элемента: ")
    try:
        formats.write_xml(user_id, filename, root)
        print("Файл создан")
    except ValueError as error:
        print(error)


def create_zip_menu(user_id):
    archive_name = input("Имя архива: ")
    line = input("Имена файлов через запятую: ")
    filenames = []
    for name in line.split(","):
        name = name.strip()
        if name:
            filenames.append(name)
    try:
        archives.create_zip(user_id, archive_name, filenames)
        print("Архив создан")
    except ValueError as error:
        print(error)


def extract_zip_menu(user_id):
    archive_name = input("Имя архива: ")
    try:
        created = archives.extract_zip(user_id, archive_name)
    except ValueError as error:
        print(error)
        return
    print("Распакованы файлы:")
    for name in created:
        print(" ", _clean(name))


def show_operations(user_id):
    rows = audit.list_operations(user_id, HISTORY_LIMIT)
    if not rows:
        print("Операций нет")
    for timestamp, operation_type, file_path in rows:
        print(f"{_local_time(timestamp)}  {operation_type:<7} {_clean(file_path)}")


def show_events(user_id):
    rows = audit.list_events(user_id, HISTORY_LIMIT)
    if not rows:
        print("Событий нет")
    for timestamp, event_type, details in rows:
        line = f"{_local_time(timestamp)}  {event_type:<14}"
        if details is not None:
            line += " " + details
        print(_clean(line))


def run():
    try:
        while True:
            user_id = auth_menu()
            if user_id is None:
                print("До свидания")
                return
            main_menu(user_id)
    except (KeyboardInterrupt, EOFError):
        print()
        print("До свидания")
