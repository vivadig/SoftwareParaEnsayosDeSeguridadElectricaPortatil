"""Esquemas DDL y migración de base de datos SQLite."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ensayos.config.config_database import database_config

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4

TABLES = {
    "schema_version": """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
    """,
    "productos": """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            descripcion TEXT DEFAULT '',
            potencia REAL NOT NULL,
            tension REAL NOT NULL,
            corriente REAL NOT NULL,
            frecuencia REAL DEFAULT 50.0,
            clase INTEGER DEFAULT 1,
            fuga_pasiva_duplicada INTEGER DEFAULT 0,
            con_cable_alimentacion INTEGER DEFAULT 1,
            tipo_aparato TEXT DEFAULT 'calefaccion'
        );
    """,
    "historial_fdl": """
        CREATE TABLE IF NOT EXISTS historial_fdl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT,
            producto TEXT,
            serial TEXT,
            fecha TEXT,
            hora TEXT,
            tension TEXT,
            a_medida TEXT,
            fp TEXT,
            w_medida TEXT,
            consumo TEXT,
            fuga_medida TEXT,
            fuga TEXT,
            cn_medido TEXT,
            cn TEXT,
            pat_medida TEXT,
            pat TEXT,
            resistida TEXT
        );
    """,
    "ensayos_consumo": """
        CREATE TABLE IF NOT EXISTS ensayos_consumo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            n_ensayo INTEGER,
            n_muestra INTEGER,
            marca TEXT,
            modelo TEXT,
            nro_serial TEXT,
            fecha TEXT,
            hora TEXT,
            tension REAL,
            corriente REAL,
            fp REAL,
            potencia_ac REAL,
            cdf REAL
        );
    """,
    "historial_verificacion": """
        CREATE TABLE IF NOT EXISTS historial_verificacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            hora TEXT,
            fuga_pasa REAL,
            pat_pasa REAL,
            rd_pasa REAL,
            fuga_falla REAL,
            pat_falla REAL,
            rd_falla REAL
        );
    """,
    "admin": """
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            contrasena TEXT NOT NULL
        );
    """,
    "correcciones": """
        CREATE TABLE IF NOT EXISTS correcciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tension REAL DEFAULT 0.0,
            corriente REAL DEFAULT 0.0,
            fuga REAL DEFAULT 0.0,
            corte_neutro REAL DEFAULT 0.0,
            puesta_a_tierra REAL DEFAULT 0.0,
            tension_resistida REAL DEFAULT 0.0
        );
    """,
    "cotas_verificacion": """
        CREATE TABLE IF NOT EXISTS cotas_verificacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fuga_pasa REAL DEFAULT 0.0,
            pat_pasa REAL DEFAULT 0.0,
            rd_pasa REAL DEFAULT 0.0,
            fuga_falla REAL DEFAULT 0.0,
            pat_falla REAL DEFAULT 0.0,
            rd_falla REAL DEFAULT 0.0
        );
    """,
    "tiempos": """
        CREATE TABLE IF NOT EXISTS tiempos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consumo_duracion INTEGER DEFAULT 5,
            consumo_unidad TEXT DEFAULT 'Segundos',
            fuga_activa_duracion INTEGER DEFAULT 5,
            fuga_activa_unidad TEXT DEFAULT 'Segundos',
            fuga_pasiva_duracion INTEGER DEFAULT 5,
            fuga_pasiva_unidad TEXT DEFAULT 'Segundos',
            pat_duracion INTEGER DEFAULT 5,
            pat_unidad TEXT DEFAULT 'Segundos',
            rigidez_duracion INTEGER DEFAULT 5,
            rigidez_unidad TEXT DEFAULT 'Segundos',
            cant_ensayos_ciclicos INTEGER DEFAULT 1,
            tiempo_entre_ensayos INTEGER DEFAULT 0,
            tiempo_entre_ensayos_unidad TEXT DEFAULT 'Segundos',
            tiempo_ensayo_consumo INTEGER DEFAULT 60,
            tiempo_ensayo_consumo_unidad TEXT DEFAULT 'Segundos',
            tiempo_entre_muestras INTEGER DEFAULT 5,
            tiempo_entre_muestras_unidad TEXT DEFAULT 'Segundos'
        );
    """,
}

DEFAULT_ADMIN = ("admin", "admin")

DEFAULT_CORRECTIONS = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

DEFAULT_COTAS_VERIFICACION = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


@contextmanager
def get_connection(db_path: str | None = None):
    """Context manager para conexiones SQLite."""
    path = db_path or database_config.path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate(cursor: sqlite3.Cursor) -> None:
    """Aplica migraciones a bases creadas con versiones anteriores del esquema."""
    # v2: condición de duplicación del límite de fuga pasiva (IEC 60335-1, 16.2)
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(productos)")}
    if "fuga_pasiva_duplicada" not in columns:
        cursor.execute("ALTER TABLE productos ADD COLUMN fuga_pasiva_duplicada INTEGER DEFAULT 0")
        logger.info("Migración v2: columna 'fuga_pasiva_duplicada' agregada a productos.")
    # v3: aparato con cable de alimentación fijo (IEC 60335-1, A.1)
    if "con_cable_alimentacion" not in columns:
        cursor.execute("ALTER TABLE productos ADD COLUMN con_cable_alimentacion INTEGER DEFAULT 1")
        logger.info("Migración v3: columna 'con_cable_alimentacion' agregada a productos.")
    # v4: tipo de aparato para tolerancias de consumo (IEC 60335-1, Tablas 1 y 2)
    if "tipo_aparato" not in columns:
        cursor.execute("ALTER TABLE productos ADD COLUMN tipo_aparato TEXT DEFAULT 'calefaccion'")
        logger.info("Migración v4: columna 'tipo_aparato' agregada a productos.")


def initialize_database(db_path: str | None = None) -> None:
    """Crea todas las tablas e inserta datos por defecto si no existen."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        for table_name, ddl in TABLES.items():
            cursor.execute(ddl)
            logger.info("Tabla '%s' verificada/creada.", table_name)

        _migrate(cursor)

        # Insertar versión del esquema si no existe
        cursor.execute("SELECT COUNT(*) FROM schema_version")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        else:
            cursor.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))

        # Insertar admin por defecto si no existe
        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO admin (usuario, contrasena) VALUES (?, ?)",
                DEFAULT_ADMIN,
            )
            logger.info("Admin por defecto creado.")

        # Insertar correcciones por defecto si no existen
        cursor.execute("SELECT COUNT(*) FROM correcciones")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """INSERT INTO correcciones
                   (tension, corriente, fuga, corte_neutro, puesta_a_tierra, tension_resistida)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                DEFAULT_CORRECTIONS,
            )

        # Insertar cotas de verificación por defecto si no existen
        cursor.execute("SELECT COUNT(*) FROM cotas_verificacion")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """INSERT INTO cotas_verificacion
                   (fuga_pasa, pat_pasa, rd_pasa, fuga_falla, pat_falla, rd_falla)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                DEFAULT_COTAS_VERIFICACION,
            )

        # Insertar tiempos por defecto si no existen
        cursor.execute("SELECT COUNT(*) FROM tiempos")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO tiempos DEFAULT VALUES")

        conn.commit()
        logger.info("Base de datos inicializada correctamente.")
