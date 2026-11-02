import hashlib
import secrets
import hmac

from file_manager.config import PBKDF2_ITERATIONS, SALT_SIZE, PBKDF2_MAX_ITERATIONS


def hash_password(password):
    """Хэширует пароль"""
    salt = secrets.token_bytes(SALT_SIZE)
    digest = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt,
        iterations=PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    """Верификация пароля"""
    try:
        algorithm, iterations, salt_hex, hash_hex = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations)
        if iterations < 1 or iterations > PBKDF2_MAX_ITERATIONS:
            return False
        digest = hashlib.pbkdf2_hmac(
            salt=bytes.fromhex(salt_hex),
            password=password.encode("utf-8"),
            iterations=iterations,
            hash_name="sha256"
        )
        return hmac.compare_digest(digest, bytes.fromhex(hash_hex))
    except ValueError:
        return False
