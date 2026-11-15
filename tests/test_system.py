import pytest

from file_manager import config
from file_manager.disks import get_disks
from file_manager.menu import _clean, _safe_text


def test_disks_are_listed():
    disks = get_disks()
    assert len(disks) > 0
    for disk in disks:
        assert set(disk) == {"device", "mountpoint", "fstype", "total", "used", "free"}
        assert disk["total"] > 0
        assert 0 <= disk["free"] <= disk["total"]


def test_service_directory_gets_private_permissions(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir(mode=0o755)
    config._ensure_dir(directory)
    assert directory.stat().st_mode & 0o777 == 0o700


def test_symlinked_service_directory_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "storage"
    link.symlink_to(real)
    with pytest.raises(RuntimeError):
        config._ensure_dir(link)


def test_terminal_escape_sequences_are_neutralized():
    assert _clean("\x1b[2J\x1b[31mred") == "?[2J?[31mred"
    assert _clean("a\rb\x07c\x00d\x7f") == "a?b?c?d?"


def test_normal_text_is_kept():
    text = "Привет, мир!\n\tстрока 2 ✓"
    assert _clean(text) == text


def test_invalid_utf8_does_not_break_output():
    assert _safe_text(b"ok \xff\xfe \x1b[0m") == "ok �� ?[0m"
