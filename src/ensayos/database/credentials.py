"""Credenciales de administrador: hash de contraseñas y verificación.

Las contraseñas se guardan con PBKDF2-SHA256 (biblioteca estándar, sin dependencias).
Se siguen aceptando contraseñas viejas en texto plano (bases migradas de FDL) para no
dejar a nadie afuera; la próxima vez que se cambian quedan con hash.
"""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "admin"


def hash_password(password: str) -> str:
    """Devuelve el hash de una contraseña en formato ``pbkdf2_sha256$iter$sal$hash``.

    Args:
        password: Contraseña en texto plano.

    Returns:
        Cadena con el algoritmo, las iteraciones, la sal y el hash, en hexadecimal.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def is_hashed(stored: str) -> bool:
    """Indica si una contraseña guardada ya está en formato hash."""
    return stored.startswith(f"{_ALGORITHM}$")


def verify_password(password: str, stored: str) -> bool:
    """Verifica una contraseña contra lo guardado (hash o texto plano heredado).

    Args:
        password: Contraseña ingresada.
        stored: Valor guardado en la base.

    Returns:
        True si coincide.
    """
    if is_hashed(stored):
        try:
            _, iterations, salt_hex, digest_hex = stored.split("$")
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
            )
        except ValueError:
            return False
        return hmac.compare_digest(digest.hex(), digest_hex)
    return hmac.compare_digest(password.strip(), stored.strip())


def is_default(user: str, stored: str) -> bool:
    """Indica si las credenciales guardadas son las de fábrica (admin/admin)."""
    return user.strip() == DEFAULT_USER and verify_password(DEFAULT_PASSWORD, stored)


def check_credentials(user: str, password: str, stored_user: str, stored: str) -> bool:
    """Verifica usuario y contraseña en tiempo constante.

    Args:
        user: Usuario ingresado.
        password: Contraseña ingresada.
        stored_user: Usuario guardado.
        stored: Contraseña guardada (hash o texto plano heredado).

    Returns:
        True si ambos coinciden.
    """
    user_ok = hmac.compare_digest(user.strip(), stored_user.strip())
    password_ok = verify_password(password, stored)
    return user_ok and password_ok
