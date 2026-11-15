import pytest

from file_manager.auth import hash_password, verify_password, validate_username, validate_password


def test_correct_password_is_accepted():
    stored = hash_password("password123")
    assert verify_password("password123", stored)


def test_incorrect_password_is_not_accepted():
    stored = hash_password("password123")
    assert not verify_password("passwo123", stored)


def test_same_password_gives_different_hashes():
    stored1 = hash_password("password123")
    stored2 = hash_password("password123")
    assert stored1 != stored2
    assert verify_password("password123", stored1)
    assert verify_password("password123", stored2)


def test_garbage_hash_is_rejected():
    stored = "abc"
    assert not verify_password("password123", stored)


def test_username_with_sql_is_rejected():
    login = "a'; DROP TABLE users;--"
    with pytest.raises(ValueError):
        validate_username(login)


def test_short_password_is_rejected():
    password = "1234567"
    with pytest.raises(ValueError):
        validate_password(password)


def test_min_length_password_is_accepted():
    password1 = "12345678"
    validate_password(password1)


def test_huge_iterations_are_rejected():
    stored = "pbkdf2_sha256$999999999999$00$00"
    assert not verify_password("password123", stored)
