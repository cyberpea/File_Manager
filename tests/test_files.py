import pytest

from file_manager.config import MAX_FILE_SIZE
from file_manager.files import (
    create_file,
    read_file,
    modify_file,
    delete_file,
    list_files,
)


def test_created_file_can_be_read(user_id):
    create_file(user_id, "notes.txt", b"hello")
    assert read_file(user_id, "notes.txt") == b"hello"


def test_create_is_recorded_in_database(user_id, operations):
    create_file(user_id, "notes.txt", b"hello")
    rows = list_files(user_id)
    assert len(rows) == 1
    assert rows[0][0] == "notes.txt"
    assert rows[0][1] == 5
    assert operations() == [("create", 1, f"{user_id}/notes.txt")]


def test_file_is_private_on_disk(sandbox, user_id):
    path = create_file(user_id, "notes.txt", b"hello")
    assert path.stat().st_mode & 0o777 == 0o600
    assert (sandbox / str(user_id)).stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("bad_path", [
    "../secret.txt",
    "../../data/file_manager.db",
    "/etc/passwd",
    "docs/../../secret.txt",
    "",
    ".",
    "..",
])
def test_path_traversal_on_read_is_rejected(user_id, events, bad_path):
    with pytest.raises(ValueError):
        read_file(user_id, bad_path)
    assert events() == [("access_denied", repr(bad_path))]


def test_null_byte_in_path_is_rejected(user_id, events):
    with pytest.raises(ValueError):
        read_file(user_id, "notes.txt\0.png")
    assert events() == [("access_denied", repr("notes.txt\0.png"))]


def test_other_users_file_cannot_be_read(user_id, other_id):
    create_file(other_id, "secret.txt", b"top secret")
    with pytest.raises(ValueError):
        read_file(user_id, f"../{other_id}/secret.txt")
    with pytest.raises(ValueError):
        read_file(user_id, "secret.txt")


def test_symlink_to_outside_is_not_followed(sandbox, tmp_path, user_id):
    create_file(user_id, "notes.txt", b"hello")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"top secret")
    (sandbox / str(user_id) / "link.txt").symlink_to(outside)
    with pytest.raises(ValueError):
        read_file(user_id, "link.txt")


@pytest.mark.parametrize("bad_name", [
    "../evil.txt",
    "sub/evil.txt",
    "/tmp/evil.txt",
    "evil\n.txt",
    "evil\x1b[31m.txt",
    "evil\0.txt",
    "evil;rm -rf.txt",
    "",
    "a" * 101,
])
def test_bad_filename_on_create_is_rejected(sandbox, user_id, bad_name):
    with pytest.raises(ValueError):
        create_file(user_id, bad_name, b"data")
    assert list_files(user_id) == []
    assert not (sandbox.parent / "evil.txt").exists()
    assert not (sandbox / "evil.txt").exists()


def test_existing_file_is_not_overwritten_by_create(user_id, operations):
    create_file(user_id, "notes.txt", b"first")
    with pytest.raises(ValueError):
        create_file(user_id, "notes.txt", b"second")
    assert read_file(user_id, "notes.txt") == b"first"
    assert len(list_files(user_id)) == 1
    assert len(operations()) == 1


def test_create_does_not_write_through_symlink(sandbox, tmp_path, user_id):
    create_file(user_id, "notes.txt", b"hello")
    outside = tmp_path / "outside.txt"
    (sandbox / str(user_id) / "trap.txt").symlink_to(outside)
    with pytest.raises(ValueError):
        create_file(user_id, "trap.txt", b"data")
    assert not outside.exists()
    assert len(list_files(user_id)) == 1


def test_too_large_data_is_rejected_on_create(user_id, events):
    with pytest.raises(ValueError):
        create_file(user_id, "big.bin", b"0" * (MAX_FILE_SIZE + 1))
    assert list_files(user_id) == []
    assert events() == [("limit_exceeded", repr("big.bin"))]


def test_file_of_max_size_is_accepted(user_id):
    create_file(user_id, "big.bin", b"0" * MAX_FILE_SIZE)
    assert len(read_file(user_id, "big.bin")) == MAX_FILE_SIZE


def test_too_large_file_is_rejected_on_read(sandbox, user_id, events):
    create_file(user_id, "big.bin", b"small")
    (sandbox / str(user_id) / "big.bin").write_bytes(b"0" * (MAX_FILE_SIZE + 1))
    with pytest.raises(ValueError):
        read_file(user_id, "big.bin")
    assert events() == [("limit_exceeded", repr("big.bin"))]


def test_missing_file_cannot_be_read(user_id):
    with pytest.raises(ValueError):
        read_file(user_id, "missing.txt")


def test_modify_changes_content_and_size(user_id, operations):
    create_file(user_id, "notes.txt", b"hello")
    modify_file(user_id, "notes.txt", b"hello world")
    assert read_file(user_id, "notes.txt") == b"hello world"
    assert list_files(user_id)[0][1] == 11
    assert [row[0] for row in operations()] == ["create", "modify"]


def test_missing_file_cannot_be_modified(sandbox, user_id):
    with pytest.raises(ValueError):
        modify_file(user_id, "missing.txt", b"data")
    assert not (sandbox / str(user_id) / "missing.txt").exists()


def test_other_users_file_cannot_be_modified_or_deleted(user_id, other_id):
    create_file(other_id, "secret.txt", b"top secret")
    with pytest.raises(ValueError):
        modify_file(user_id, "secret.txt", b"hacked")
    with pytest.raises(ValueError):
        delete_file(user_id, "secret.txt")
    assert read_file(other_id, "secret.txt") == b"top secret"


def test_delete_removes_file_and_keeps_history(user_id, operations):
    path = create_file(user_id, "notes.txt", b"hello")
    delete_file(user_id, "notes.txt")
    assert not path.exists()
    assert list_files(user_id) == []
    assert operations() == [
        ("create", None, f"{user_id}/notes.txt"),
        ("delete", None, f"{user_id}/notes.txt"),
    ]


def test_missing_file_cannot_be_deleted(user_id):
    with pytest.raises(ValueError):
        delete_file(user_id, "missing.txt")


def test_list_shows_only_own_files(user_id, other_id):
    create_file(user_id, "mine.txt", b"1")
    create_file(other_id, "theirs.txt", b"2")
    assert [row[0] for row in list_files(user_id)] == ["mine.txt"]
    assert [row[0] for row in list_files(other_id)] == ["theirs.txt"]
