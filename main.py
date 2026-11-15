from file_manager.config import ensure_directories
from file_manager.db import init_db
from file_manager.menu import run


def main():
    ensure_directories()
    init_db()
    run()


if __name__ == "__main__":
    main()
