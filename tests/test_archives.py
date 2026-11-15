import io
import os
import zipfile

import pytest

from file_manager import archives
from file_manager.archives import create_zip, extract_zip
from file_manager.config import ZIP_MAX_FILES
from file_manager.files import create_file, read_file, delete_file, list_files


def make_zip(entries, compression=zipfile.ZIP_DEFLATED):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=compression) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


def names(user_id):
    return [row[0] for row in list_files(user_id)]


def test_zip_roundtrip(user_id):
    create_file(user_id, "a.txt", b"first")
    create_file(user_id, "b.txt", b"second")
    create_zip(user_id, "pack.zip", ["a.txt", "b.txt"])
    delete_file(user_id, "a.txt")
    delete_file(user_id, "b.txt")
    assert extract_zip(user_id, "pack.zip") == ["a.txt", "b.txt"]
    assert read_file(user_id, "a.txt") == b"first"
    assert read_file(user_id, "b.txt") == b"second"


def test_empty_list_is_not_archived(user_id):
    with pytest.raises(ValueError):
        create_zip(user_id, "pack.zip", [])


def test_repeated_names_are_not_archived(user_id):
    create_file(user_id, "a.txt", b"first")
    with pytest.raises(ValueError):
        create_zip(user_id, "pack.zip", ["a.txt", "a.txt"])
    assert names(user_id) == ["a.txt"]


def test_missing_file_is_not_archived(user_id):
    create_file(user_id, "a.txt", b"first")
    with pytest.raises(ValueError):
        create_zip(user_id, "pack.zip", ["a.txt", "missing.txt"])
    assert names(user_id) == ["a.txt"]


def test_file_outside_sandbox_is_not_archived(user_id):
    with pytest.raises(ValueError):
        create_zip(user_id, "pack.zip", ["../../data/file_manager.db"])
    assert names(user_id) == []


def test_too_many_files_are_not_archived(user_id, events):
    filenames = [f"{number}.txt" for number in range(ZIP_MAX_FILES + 1)]
    with pytest.raises(ValueError):
        create_zip(user_id, "pack.zip", filenames)
    assert events()[0][0] == "limit_exceeded"


def test_not_a_zip_is_rejected(user_id):
    create_file(user_id, "fake.zip", b"this is not a zip archive")
    with pytest.raises(ValueError):
        extract_zip(user_id, "fake.zip")


@pytest.mark.parametrize("evil_name", [
    "../evil.txt",
    "../../evil.txt",
    "/tmp/evil.txt",
    "sub/evil.txt",
    "..\\evil.txt",
    "evil\n.txt",
])
def test_zip_slip_is_rejected(sandbox, user_id, events, evil_name):
    create_file(user_id, "slip.zip", make_zip([("good.txt", b"ok"), (evil_name, b"pwned")]))
    with pytest.raises(ValueError):
        extract_zip(user_id, "slip.zip")
    assert names(user_id) == ["slip.zip"]
    assert not (sandbox / "evil.txt").exists()
    assert not (sandbox.parent / "evil.txt").exists()
    assert events() == [("access_denied", repr("slip.zip"))]


def test_directory_entry_is_rejected(user_id):
    create_file(user_id, "dirs.zip", make_zip([("folder/", b"")]))
    with pytest.raises(ValueError):
        extract_zip(user_id, "dirs.zip")
    assert names(user_id) == ["dirs.zip"]


def test_zip_bomb_by_ratio_is_rejected(user_id, events):
    bomb = make_zip([("bomb.bin", b"\0" * (5 * 1024 * 1024))])
    assert len(bomb) < 10 * 1024
    create_file(user_id, "bomb.zip", bomb)
    with pytest.raises(ValueError):
        extract_zip(user_id, "bomb.zip")
    assert names(user_id) == ["bomb.zip"]
    assert events() == [("limit_exceeded", repr("bomb.zip"))]


def test_too_many_entries_are_rejected(user_id, events):
    entries = [(f"{number}.txt", b"x") for number in range(ZIP_MAX_FILES + 1)]
    create_file(user_id, "many.zip", make_zip(entries))
    with pytest.raises(ValueError):
        extract_zip(user_id, "many.zip")
    assert names(user_id) == ["many.zip"]
    assert events() == [("limit_exceeded", repr("many.zip"))]


def test_total_size_limit_is_enforced(user_id, events, monkeypatch):
    monkeypatch.setattr(archives, "ZIP_MAX_TOTAL_SIZE", 1000)
    entries = [("a.bin", os.urandom(600)), ("b.bin", os.urandom(600))]
    create_file(user_id, "fat.zip", make_zip(entries))
    with pytest.raises(ValueError):
        extract_zip(user_id, "fat.zip")
    assert names(user_id) == ["fat.zip"]
    assert events() == [("limit_exceeded", repr("fat.zip"))]


def test_too_large_entry_is_rejected(user_id, monkeypatch):
    monkeypatch.setattr(archives, "MAX_FILE_SIZE", 100)
    create_file(user_id, "big.zip", make_zip([("big.bin", os.urandom(200))]))
    with pytest.raises(ValueError):
        extract_zip(user_id, "big.zip")
    assert names(user_id) == ["big.zip"]


@pytest.mark.filterwarnings("ignore:Duplicate name")
def test_repeated_names_in_archive_are_rejected(user_id):
    create_file(user_id, "dup.zip", make_zip([("a.txt", b"one"), ("a.txt", b"two")]))
    with pytest.raises(ValueError):
        extract_zip(user_id, "dup.zip")
    assert names(user_id) == ["dup.zip"]


def test_corrupted_archive_is_rejected(user_id):
    data = bytearray(make_zip([("a.txt", b"hello world")], compression=zipfile.ZIP_STORED))
    position = data.index(b"hello world")
    data[position] = ord("j")
    create_file(user_id, "broken.zip", bytes(data))
    with pytest.raises(ValueError):
        extract_zip(user_id, "broken.zip")
    assert names(user_id) == ["broken.zip"]


def test_existing_file_is_not_overwritten_and_extraction_is_rolled_back(user_id):
    create_file(user_id, "b.txt", b"original")
    create_file(user_id, "pack.zip", make_zip([("a.txt", b"new a"), ("b.txt", b"new b"), ("c.txt", b"new c")]))
    with pytest.raises(ValueError):
        extract_zip(user_id, "pack.zip")
    assert names(user_id) == ["b.txt", "pack.zip"]
    assert read_file(user_id, "b.txt") == b"original"


def test_other_users_archive_cannot_be_extracted(user_id, other_id):
    create_file(other_id, "pack.zip", make_zip([("a.txt", b"data")]))
    with pytest.raises(ValueError):
        extract_zip(user_id, "pack.zip")
    assert names(user_id) == []
