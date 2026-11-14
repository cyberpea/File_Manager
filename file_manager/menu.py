import getpass

from file_manager import auth


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


def run():
    try:
        user_id = auth_menu()
        if user_id is None:
            print("До свидания")
            return
        print(f"Вход выполнен, id = {user_id}")
    except (KeyboardInterrupt, EOFError):
        print()
        print("До свидания")
