import io
import zipfile
import zlib

from file_manager.config import ZIP_MAX_FILES, ZIP_MAX_TOTAL_SIZE, ZIP_MAX_RATIO, MAX_FILE_SIZE
from file_manager.audit import log_event
from file_manager.files import validate_filename, read_file, create_file, delete_file


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


def extract_zip(user_id, archive_name):
    """Распаковывает zip-архив"""
    data = read_file(user_id, archive_name)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Файл не является корректным zip-архивом") from None
    with archive:
        members = archive.infolist()
        if len(members) > ZIP_MAX_FILES:
            log_event("limit_exceeded", user_id, repr(archive_name))
            raise ValueError("Слишком большое количество файлов в архиве")
        total = 0
        names = []
        for info in members:
            if info.is_dir():
                raise ValueError("Архив содержит папки")
            try:
                validate_filename(info.filename)
            except ValueError:
                log_event("access_denied", user_id, repr(archive_name))
                raise ValueError("Недопустимое имя файла в архиве") from None
            if info.filename in names:
                raise ValueError("Имена файлов в архиве повторяются")
            total += info.file_size
            if total > ZIP_MAX_TOTAL_SIZE:
                log_event("limit_exceeded", user_id, repr(archive_name))
                raise ValueError("Превышение допустимого размера архива")
            if (info.compress_size * ZIP_MAX_RATIO) < info.file_size:
                log_event("limit_exceeded", user_id, repr(archive_name))
                raise ValueError("Слишком большой коэффициент сжатия")
            names.append(info.filename)
        contents = []
        real_total = 0
        for info in members:
            try:
                with archive.open(info) as member:
                    data = member.read(MAX_FILE_SIZE + 1)
            except (zipfile.BadZipFile, zlib.error, RuntimeError, EOFError):
                raise ValueError("Архив поврежден или не поддерживается") from None
            if len(data) > MAX_FILE_SIZE:
                log_event("limit_exceeded", user_id, repr(archive_name))
                raise ValueError("Слишком большой файл внутри архива")
            real_total += len(data)
            if real_total > ZIP_MAX_TOTAL_SIZE:
                log_event("limit_exceeded", user_id, repr(archive_name))
                raise ValueError("Превышение допустимого размера архива")
            contents.append((info.filename, data))
    created = []
    try:
        for name, data in contents:
            create_file(user_id, name, data)
            created.append(name)
    except ValueError:
        for name in created:
            delete_file(user_id, name)
        raise
    return created
