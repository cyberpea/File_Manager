import io
import zipfile

from file_manager.config import ZIP_MAX_FILES, ZIP_MAX_TOTAL_SIZE
from file_manager.audit import log_event
from file_manager.files import validate_filename, read_file, create_file


def create_zip(user_id, archive_name, filenames):
    """Собирает zip-архив из файлов пользователя"""
    if not filenames:
        raise ValueError("Отсутствуют файлы для сжатия")
    elif len(filenames) > ZIP_MAX_FILES:
        log_event("limit_exceeded", user_id, repr(filenames))
        raise ValueError("Превышение допустимого количества файлов для сжатия")
    if len(set(filenames)) < len(filenames):
        raise ValueError("Имена файлов в списке повторяются")
    for filename in filenames:
        validate_filename(filename)
    buffer = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in filenames:
            data = read_file(user_id, filename)
            total += len(data)
            if total > ZIP_MAX_TOTAL_SIZE:
                log_event("limit_exceeded", user_id, repr(archive_name))
                raise ValueError("Превышение допустимого размера архива")
            archive.writestr(filename, data)
    return create_file(user_id, archive_name, buffer.getvalue())
