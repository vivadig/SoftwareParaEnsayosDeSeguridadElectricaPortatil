"""Tests del límite de fuga pasiva (IEC 60335-1, 16.2)."""

import sqlite3
from unittest.mock import MagicMock

from ensayos.database.schemas import SCHEMA_VERSION, initialize_database
from ensayos.database.sqlite_repository import SQLiteProductRepository
from ensayos.engine.test_runner import TestRunner
from ensayos.engine.tests.passive_leakage import PassiveLeakageTest
from ensayos.engine.verdict import evaluate_passive_leakage
from ensayos.models.enums import DeviceClass, TestType, Verdict
from ensayos.models.product import Product


def _product(**kwargs) -> Product:
    defaults = {
        "marca": "Marca",
        "modelo": "Modelo",
        "descripcion": "",
        "potencia": 1000.0,
        "tension": 220.0,
        "corriente": 4.5,
        "frecuencia": 50.0,
        "clase": DeviceClass.CLASS_1,
    }
    defaults.update(kwargs)
    return Product(**defaults)


class TestEvaluatePassiveLeakage:
    """Pruebas de la función pura de veredicto."""

    def test_limite_base_750_ua(self) -> None:
        assert evaluate_passive_leakage(749.0) == Verdict.OK
        assert evaluate_passive_leakage(750.0) == Verdict.FAIL

    def test_1000_ua_falla_sin_condicion_de_duplicacion(self) -> None:
        # Antes pasaba con el límite fijo de 1500 μA
        assert evaluate_passive_leakage(1000.0) == Verdict.FAIL

    def test_limite_duplicado_1500_ua(self) -> None:
        assert evaluate_passive_leakage(1000.0, doubled_limit=True) == Verdict.OK
        assert evaluate_passive_leakage(1500.0, doubled_limit=True) == Verdict.FAIL


def test_runner_pasa_la_condicion_del_producto() -> None:
    runner = TestRunner(hardware=MagicMock())
    product = _product(fuga_pasiva_duplicada=True)
    test = runner._create_test(TestType.PASSIVE_LEAKAGE, product)
    assert isinstance(test, PassiveLeakageTest)
    assert test.doubled_limit is True


class TestPersistencia:
    """Pruebas de la columna nueva y su migración."""

    def test_producto_conserva_la_condicion(self, tmp_path) -> None:
        db = str(tmp_path / "ensayos.db")
        initialize_database(db)
        repo = SQLiteProductRepository(db)
        assert repo.create(_product(fuga_pasiva_duplicada=True))

        stored = repo.get_by_brand_model("Marca", "Modelo")
        assert stored.fuga_pasiva_duplicada is True

        stored.fuga_pasiva_duplicada = False
        assert repo.update(stored)
        assert repo.get_by_id(stored.id).fuga_pasiva_duplicada is False

    def test_migra_base_con_esquema_v1(self, tmp_path) -> None:
        db = str(tmp_path / "ensayos.db")
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version VALUES (1);
            CREATE TABLE productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marca TEXT NOT NULL, modelo TEXT NOT NULL, descripcion TEXT DEFAULT '',
                potencia REAL NOT NULL, tension REAL NOT NULL, corriente REAL NOT NULL,
                frecuencia REAL DEFAULT 50.0, clase INTEGER DEFAULT 1
            );
            INSERT INTO productos (marca, modelo, potencia, tension, corriente)
                VALUES ('Vieja', 'P1', 100, 220, 0.5);
            """
        )
        conn.close()

        initialize_database(db)

        product = SQLiteProductRepository(db).get_by_brand_model("Vieja", "P1")
        assert product.fuga_pasiva_duplicada is False
        conn = sqlite3.connect(db)
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION
        conn.close()
