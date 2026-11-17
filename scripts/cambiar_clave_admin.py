#!/usr/bin/env python3
"""Cambia el usuario y la contraseña de administrador (API y panel de administración).

La contraseña se pide por teclado (no queda en el historial de la terminal) y se guarda
con hash. Mientras sigan las credenciales de fábrica (admin/admin), la API rechaza las
consultas protegidas.

Uso:
    uv run python scripts/cambiar_clave_admin.py
    uv run python scripts/cambiar_clave_admin.py --usuario operador --db data/ensayos.db
"""

import argparse
import getpass
import sys
from pathlib import Path

# Permite importar el paquete sin instalarlo
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ensayos.config.config_database import database_config  # noqa: E402
from ensayos.database.credentials import DEFAULT_PASSWORD  # noqa: E402
from ensayos.database.schemas import initialize_database  # noqa: E402
from ensayos.database.sqlite_repository import SQLiteConfigRepository  # noqa: E402

MIN_LENGTH = 8


def main() -> int:
    """Pide la nueva contraseña, la valida y la guarda.

    Returns:
        Código de salida: 0 si se guardó, 1 si no.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default=database_config.path, help="ruta de la base de datos")
    parser.add_argument("--usuario", help="nuevo usuario (por defecto, se conserva el actual)")
    args = parser.parse_args()

    initialize_database(args.db)
    repo = SQLiteConfigRepository(args.db)
    actual = repo.get_admin_credentials()
    usuario = (args.usuario or (actual[0] if actual else "admin")).strip()
    print(f"Base: {args.db}\nUsuario: {usuario}")

    clave = getpass.getpass("Nueva contraseña: ")
    if len(clave) < MIN_LENGTH:
        print(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres.")
        return 1
    if clave in (DEFAULT_PASSWORD, usuario):
        print("La contraseña no puede ser la de fábrica ni igual al usuario.")
        return 1
    if getpass.getpass("Repetir contraseña: ") != clave:
        print("Las contraseñas no coinciden.")
        return 1

    if not repo.set_admin_credentials(usuario, clave):
        print("No se pudo guardar.")
        return 1
    print("Credenciales actualizadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
