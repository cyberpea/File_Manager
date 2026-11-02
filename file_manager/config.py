from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "file_manager.db"


def ensure_directories():
    """Создает необходимые директории для запуска"""
    STORAGE_DIR.mkdir(mode=0o700, exist_ok=True)
    DATA_DIR.mkdir(mode=0o700, exist_ok=True)
    # Запуск проверки на симлинки и смена прав при наличии директорий
    _ensure_dir(STORAGE_DIR)
    _ensure_dir(DATA_DIR)


def _ensure_dir(path):
    """Меняет права доступа, проверяет на симлинки"""
    if path.is_symlink():
        raise RuntimeError("Служебный каталог оказался симлинком, запуск остановлен.")
    path.chmod(0o700)
