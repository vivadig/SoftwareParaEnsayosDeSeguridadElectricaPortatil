"""Implementación SQLite de los repositorios de datos."""

import logging

from ensayos.database.schemas import get_connection
from ensayos.models.enums import DeviceClass
from ensayos.models.product import Product
from ensayos.models.test_result import ConsumptionSample, FdlTestRecord

logger = logging.getLogger(__name__)


class SQLiteProductRepository:
    """Repositorio de productos usando SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def create(self, product: Product) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO productos
                       (marca, modelo, descripcion, potencia, tension, corriente, frecuencia, clase)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        product.marca,
                        product.modelo,
                        product.descripcion,
                        product.potencia,
                        product.tension,
                        product.corriente,
                        product.frecuencia,
                        product.clase.value,
                    ),
                )
            return True
        except Exception as e:
            logger.error("Error al crear producto: %s", e)
            return False

    def get_by_id(self, product_id: int) -> Product | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM productos WHERE id = ?", (product_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_product(row)

    def get_by_brand_model(self, marca: str, modelo: str) -> Product | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM productos WHERE marca = ? AND modelo = ?",
                (marca, modelo),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_product(row)

    def list_all(self) -> list[Product]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM productos").fetchall()
        return [self._row_to_product(row) for row in rows]

    def update(self, product: Product) -> bool:
        if product.id is None:
            return False
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """UPDATE productos SET marca=?, modelo=?, descripcion=?,
                       potencia=?, tension=?, corriente=?, frecuencia=?, clase=?
                       WHERE id=?""",
                    (
                        product.marca,
                        product.modelo,
                        product.descripcion,
                        product.potencia,
                        product.tension,
                        product.corriente,
                        product.frecuencia,
                        product.clase.value,
                        product.id,
                    ),
                )
            return True
        except Exception as e:
            logger.error("Error al actualizar producto: %s", e)
            return False

    def delete(self, product_id: int) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute("DELETE FROM productos WHERE id = ?", (product_id,))
            return True
        except Exception as e:
            logger.error("Error al eliminar producto: %s", e)
            return False

    @staticmethod
    def _row_to_product(row) -> Product:
        return Product(
            id=row["id"],
            marca=row["marca"],
            modelo=row["modelo"],
            descripcion=row["descripcion"] or "",
            potencia=row["potencia"],
            tension=row["tension"],
            corriente=row["corriente"],
            frecuencia=row["frecuencia"],
            clase=DeviceClass(row["clase"]),
        )


class SQLiteFdlHistoryRepository:
    """Repositorio de historial de ensayos Final de Línea."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def save(self, record: FdlTestRecord) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO historial_fdl
                       (marca, producto, serial, fecha, hora, tension, a_medida, fp,
                        w_medida, consumo, fuga_medida, fuga, cn_medido, cn,
                        pat_medida, pat, resistida)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.marca,
                        record.modelo,
                        record.serial,
                        record.fecha,
                        record.hora,
                        str(record.tension),
                        str(record.corriente),
                        str(record.factor_potencia),
                        str(record.potencia),
                        record.veredicto_consumo.value,
                        str(record.fuga_activa_medida),
                        record.veredicto_fuga_activa.value,
                        str(record.fuga_pasiva_medida),
                        record.veredicto_fuga_pasiva.value,
                        str(record.pat_medida),
                        record.veredicto_pat.value,
                        record.veredicto_rigidez.value,
                    ),
                )
            return True
        except Exception as e:
            logger.error("Error al guardar historial FDL: %s", e)
            return False

    def list_all(self) -> list[dict]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM historial_fdl ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def search(
        self,
        fecha: str | None = None,
        marca: str | None = None,
        query: str | None = None,
    ) -> list[dict]:
        conditions = []
        params = []
        if fecha:
            conditions.append("fecha = ?")
            params.append(fecha)
        if marca:
            conditions.append("marca = ?")
            params.append(marca)
        if query:
            conditions.append(
                "(marca LIKE ? OR producto LIKE ? OR serial LIKE ?)"
            )
            like = f"%{query}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM historial_fdl WHERE {where} ORDER BY id DESC"

        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete_all(self) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute("DELETE FROM historial_fdl")
            return True
        except Exception as e:
            logger.error("Error al borrar historial FDL: %s", e)
            return False


class SQLiteConsumptionHistoryRepository:
    """Repositorio de historial de ensayos de consumo."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def save(self, sample: ConsumptionSample) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO ensayos_consumo
                       (n_ensayo, n_muestra, marca, modelo, nro_serial, fecha, hora,
                        tension, corriente, fp, potencia_ac, cdf)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        sample.n_ensayo,
                        sample.n_muestra,
                        sample.marca,
                        sample.modelo,
                        sample.serial,
                        sample.fecha,
                        sample.hora,
                        sample.tension,
                        sample.corriente,
                        sample.factor_potencia,
                        sample.potencia,
                        sample.fuga_activa,
                    ),
                )
            return True
        except Exception as e:
            logger.error("Error al guardar muestra de consumo: %s", e)
            return False

    def list_all(self) -> list[dict]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM ensayos_consumo ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def search(
        self,
        fecha: str | None = None,
        query: str | None = None,
    ) -> list[dict]:
        conditions = []
        params = []
        if fecha:
            conditions.append("fecha = ?")
            params.append(fecha)
        if query:
            conditions.append(
                "(marca LIKE ? OR modelo LIKE ? OR nro_serial LIKE ?)"
            )
            like = f"%{query}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM ensayos_consumo WHERE {where} ORDER BY id DESC"

        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete_all(self) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute("DELETE FROM ensayos_consumo")
            return True
        except Exception as e:
            logger.error("Error al borrar historial consumo: %s", e)
            return False


class SQLiteVerificationHistoryRepository:
    """Repositorio de historial de verificación."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def save(
        self,
        fecha: str,
        hora: str,
        fuga_pasa: float,
        pat_pasa: float,
        rd_pasa: float,
        fuga_falla: float,
        pat_falla: float,
        rd_falla: float,
    ) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO historial_verificacion
                       (fecha, hora, fuga_pasa, pat_pasa, rd_pasa,
                        fuga_falla, pat_falla, rd_falla)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fecha, hora, fuga_pasa, pat_pasa, rd_pasa,
                     fuga_falla, pat_falla, rd_falla),
                )
            return True
        except Exception as e:
            logger.error("Error al guardar verificación: %s", e)
            return False

    def list_all(self) -> list[dict]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM historial_verificacion ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]


class SQLiteConfigRepository:
    """Repositorio de configuración persistida en DB."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    # --- Correcciones ---

    def get_corrections(self) -> dict:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM correcciones WHERE id = 1").fetchone()
        return dict(row) if row else {}

    def save_corrections(
        self,
        tension: float,
        corriente: float,
        fuga: float,
        corte_neutro: float,
        puesta_a_tierra: float,
        tension_resistida: float,
    ) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """UPDATE correcciones SET tension=?, corriente=?, fuga=?,
                       corte_neutro=?, puesta_a_tierra=?, tension_resistida=?
                       WHERE id = 1""",
                    (tension, corriente, fuga, corte_neutro, puesta_a_tierra, tension_resistida),
                )
            return True
        except Exception as e:
            logger.error("Error al guardar correcciones: %s", e)
            return False

    # --- Tiempos ---

    def get_timings(self) -> dict:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM tiempos WHERE id = 1").fetchone()
        return dict(row) if row else {}

    def save_timings(self, **kwargs) -> bool:
        if not kwargs:
            return False
        set_clauses = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values())
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    f"UPDATE tiempos SET {set_clauses} WHERE id = 1",  # noqa: S608
                    values,
                )
            return True
        except Exception as e:
            logger.error("Error al guardar tiempos: %s", e)
            return False

    # --- Patrones de verificación ---

    def get_verification_patterns(self) -> dict:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM cotas_verificacion WHERE id = 1"
            ).fetchone()
        return dict(row) if row else {}

    def save_verification_patterns(
        self,
        fuga_pasa: float,
        pat_pasa: float,
        rd_pasa: float,
        fuga_falla: float,
        pat_falla: float,
        rd_falla: float,
    ) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """UPDATE cotas_verificacion SET fuga_pasa=?, pat_pasa=?, rd_pasa=?,
                       fuga_falla=?, pat_falla=?, rd_falla=?
                       WHERE id = 1""",
                    (fuga_pasa, pat_pasa, rd_pasa, fuga_falla, pat_falla, rd_falla),
                )
            return True
        except Exception as e:
            logger.error("Error al guardar patrones verificación: %s", e)
            return False

    # --- Admin ---

    def get_admin_credentials(self) -> tuple[str, str] | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT usuario, contrasena FROM admin WHERE id = 1").fetchone()
        if row is None:
            return None
        return (row["usuario"], row["contrasena"])

    def set_admin_password(self, new_password: str) -> bool:
        try:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    "UPDATE admin SET contrasena = ? WHERE id = 1",
                    (new_password,),
                )
            return True
        except Exception as e:
            logger.error("Error al cambiar contraseña: %s", e)
            return False
