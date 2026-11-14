import getpass

from file_manager import auth
from file_manager import disks


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
        print("0. Выйти из аккаунта")
        choice = input("> ").strip()

        if choice == "1":
            show_disks()
        elif choice == "0":
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
