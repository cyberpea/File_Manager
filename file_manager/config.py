from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "file_manager.db"
PBKDF2_ITERATIONS = 600_000
PBKDF2_MAX_ITERATIONS = 2_000_000
SALT_SIZE = 16
USERNAME_PATTERN = r"[A-Za-z0-9_]{3,32}"
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
AUDIT_EVENT_TYPES = {"register", "login_success", "login_failed", "access_denied", "limit_exceeded"}
AUDIT_DETAILS_MAX_LENGTH = 500
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_MINUTES = 15
MAX_FILE_SIZE = 10 * 1024 * 1024
FILENAME_PATTERN = r"[\w.\- ]{1,100}"
JSON_MAX_DEPTH = 50
XML_MAX_DEPTH = 50
XML_NAME_PATTERN = r"[A-Za-z_][A-Za-z0-9_.\-]{0,63}"
ZIP_MAX_FILES = 100
ZIP_MAX_TOTAL_SIZE = 50 * 1024 * 1024
ZIP_MAX_RATIO = 100


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
