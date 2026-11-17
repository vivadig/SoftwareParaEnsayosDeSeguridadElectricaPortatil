"""Tests de las credenciales de administrador (hash, verificación y credenciales de fábrica)."""

import pytest

from ensayos.database.credentials import (
    check_credentials,
    hash_password,
    is_default,
    is_hashed,
    verify_password,
)
from ensayos.database.schemas import initialize_database
from ensayos.database.sqlite_repository import SQLiteConfigRepository


def test_hash_y_verificacion():
    stored = hash_password("clave-segura-1")
    assert is_hashed(stored)
    assert "clave-segura-1" not in stored
    assert verify_password("clave-segura-1", stored)
    assert not verify_password("otra", stored)


def test_misma_clave_genera_hashes_distintos():
    assert hash_password("x") != hash_password("x")


def test_texto_plano_heredado_sigue_funcionando():
    assert verify_password("vieja", "vieja")
    assert not verify_password("otra", "vieja")


def test_hash_corrupto_no_valida():
    assert not verify_password("x", "pbkdf2_sha256$no$es$valido")


def test_credenciales_de_fabrica():
    assert is_default("admin", "admin")
    assert is_default("admin", hash_password("admin"))
    assert not is_default("admin", hash_password("otra-clave"))
    assert not is_default("operador", "admin")


def test_check_credentials():
    stored = hash_password("clave-segura-1")
    assert check_credentials("operador", "clave-segura-1", "operador", stored)
    assert not check_credentials("intruso", "clave-segura-1", "operador", stored)
    assert not check_credentials("operador", "mal", "operador", stored)


def test_repositorio_guarda_con_hash(tmp_path):
    db = str(tmp_path / "e.db")
    initialize_database(db)
    repo = SQLiteConfigRepository(db)
    assert repo.get_admin_credentials() == ("admin", "admin")  # fábrica
    assert repo.set_admin_credentials("operador", "clave-segura-1")
    usuario, stored = repo.get_admin_credentials()
    assert usuario == "operador" and is_hashed(stored)
    assert verify_password("clave-segura-1", stored)
    assert repo.set_admin_password("clave-segura-2")
    assert verify_password("clave-segura-2", repo.get_admin_credentials()[1])


def test_api_rechaza_credenciales_de_fabrica(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi import HTTPException
    from fastapi.security import HTTPBasicCredentials

    from ensayos.api import auth

    db = str(tmp_path / "e.db")
    initialize_database(db)
    repo = SQLiteConfigRepository(db)
    auth.set_config_repository(repo)

    with pytest.raises(HTTPException) as e:
        auth.verify_credentials(HTTPBasicCredentials(username="admin", password="admin"))
    assert e.value.status_code == 503

    repo.set_admin_credentials("operador", "clave-segura-1")
    ok = HTTPBasicCredentials(username="operador", password="clave-segura-1")
    assert auth.verify_credentials(ok) == "operador"
    with pytest.raises(HTTPException) as e:
        auth.verify_credentials(HTTPBasicCredentials(username="operador", password="mal"))
    assert e.value.status_code == 401
