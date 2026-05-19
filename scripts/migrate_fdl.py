#!/usr/bin/env python3
"""Script de migración de datos desde FDL (3 DBs separadas) al nuevo esquema unificado.

Uso:
    python scripts/migrate_fdl.py --fdl-dir /path/to/FDL-windows-main/data --output data/ensayos.db

Lee:
    - database.db      → productos, admin, correcciones, cotas_verificacion, tiempos,
                          historial_verificacion, cotas
    - historial_fdl.db → historial FDL
    - historial_consumo.db → ensayos de consumo
"""

import argparse
import ast
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def migrate(fdl_dir: str, output_path: str) -> None:
    """Ejecuta la migración completa."""
    fdl_path = Path(fdl_dir)
    main_db = fdl_path / "database.db"
    fdl_db = fdl_path / "historial_fdl.db"
    consumo_db = fdl_path / "historial_consumo.db"

    # Verificar que existan las DBs fuente
    for db_file in [main_db, fdl_db, consumo_db]:
        if not db_file.exists():
            logger.warning("No se encontró %s — se omitirá.", db_file)

    # Crear directorio de salida si no existe
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Inicializar la nueva DB con el esquema
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from ensayos.database.schemas import initialize_database
    initialize_database(output_path)

    dest = sqlite3.connect(output_path)
    dest.row_factory = sqlite3.Row

    try:
        # --- Migrar productos ---
        if main_db.exists():
            src = sqlite3.connect(str(main_db))
            src.row_factory = sqlite3.Row

            rows = src.execute("SELECT * FROM productos").fetchall()
            count = 0
            for row in rows:
                dest.execute(
                    """INSERT INTO productos
                       (marca, modelo, descripcion, potencia, tension, corriente, frecuencia, clase)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["marca"], row["modelo"], row["descripcion"],
                     row["potencia"], row["tension"], row["corriente"],
                     row["frecuencia"], row["clase"]),
                )
                count += 1
            logger.info("Migrados %d productos.", count)

            # --- Migrar admin ---
            admin_rows = src.execute("SELECT * FROM admin").fetchall()
            if admin_rows:
                row = admin_rows[0]
                dest.execute(
                    "UPDATE admin SET usuario = ?, contrasena = ? WHERE id = 1",
                    (row["usuario"], row["contrasena"]),
                )
                logger.info("Admin migrado (contraseña en texto plano — considere hashearla).")

            # --- Migrar correcciones ---
            corr_rows = src.execute("SELECT * FROM correcciones").fetchall()
            if corr_rows:
                row = corr_rows[0]
                dest.execute(
                    """UPDATE correcciones SET tension=?, corriente=?, fuga=?,
                       corte_neutro=?, puesta_a_tierra=?, tension_resistida=?
                       WHERE id = 1""",
                    (row["tension"], row["corriente"], row["fuga"],
                     row["corte_neutro"], row["puesta_a_tierra"], row["tension_resistida"]),
                )
                logger.info("Correcciones migradas.")

            # --- Migrar cotas de verificación ---
            try:
                cotas_rows = src.execute("SELECT * FROM cotasverificacion").fetchall()
                if cotas_rows:
                    row = cotas_rows[0]
                    dest.execute(
                        """UPDATE cotas_verificacion SET fuga_pasa=?, pat_pasa=?, rd_pasa=?,
                           fuga_falla=?, pat_falla=?, rd_falla=?
                           WHERE id = 1""",
                        (row["fuga_pasa"], row["pat_pasa"], row["rd_pasa"],
                         row["fuga_falla"], row["pat_falla"], row["rd_falla"]),
                    )
                    logger.info("Cotas de verificación migradas.")
            except Exception as e:
                logger.warning("No se pudieron migrar cotas de verificación: %s", e)

            # --- Migrar tiempos (convirtiendo formato stringificado) ---
            try:
                tiempos_rows = src.execute("SELECT * FROM tiempos").fetchall()
                if tiempos_rows:
                    row = tiempos_rows[0]
                    # FDL guarda tiempos como strings de listas Python: '["5", "Segundos"]'
                    fields = list(row.keys())[1:]  # Omitir 'id'
                    parsed = {}
                    for field in fields:
                        val = row[field]
                        if isinstance(val, str):
                            try:
                                parsed_val = ast.literal_eval(val)
                                if isinstance(parsed_val, list) and len(parsed_val) == 2:
                                    # Mapear al nuevo esquema
                                    field_map = {
                                        "funcionamiento_fdl": ("consumo_duracion", "consumo_unidad"),
                                        "fuga_activa_fdl": ("fuga_activa_duracion", "fuga_activa_unidad"),
                                        "fuga_pasiva_fdl": ("fuga_pasiva_duracion", "fuga_pasiva_unidad"),
                                        "puesta_a_tierra_fdl": ("pat_duracion", "pat_unidad"),
                                        "rigidez_dielectrica_fdl": ("rigidez_duracion", "rigidez_unidad"),
                                        "cant_ensayos": ("cant_ensayos_ciclicos", None),
                                        "tiempo_entre_ensayos": ("tiempo_entre_ensayos", "tiempo_entre_ensayos_unidad"),
                                        "tiempo_ensayo_consumo": ("tiempo_ensayo_consumo", "tiempo_ensayo_consumo_unidad"),
                                        "tiempo_entre_muestras": ("tiempo_entre_muestras", "tiempo_entre_muestras_unidad"),
                                    }
                                    if field in field_map:
                                        dur_field, unit_field = field_map[field]
                                        parsed[dur_field] = int(parsed_val[0])
                                        if unit_field:
                                            parsed[unit_field] = parsed_val[1]
                            except (ValueError, SyntaxError):
                                pass
                        else:
                            # Valor directo (no stringificado)
                            pass

                    if parsed:
                        set_clauses = ", ".join(f"{k} = ?" for k in parsed)
                        dest.execute(
                            f"UPDATE tiempos SET {set_clauses} WHERE id = 1",
                            list(parsed.values()),
                        )
                        logger.info("Tiempos migrados y convertidos a columnas tipadas.")
            except Exception as e:
                logger.warning("No se pudieron migrar tiempos: %s", e)

            # --- Migrar historial de verificación ---
            try:
                verif_rows = src.execute("SELECT * FROM historialverificacion").fetchall()
                count = 0
                for row in verif_rows:
                    dest.execute(
                        """INSERT INTO historial_verificacion
                           (fecha, hora, fuga_pasa, pat_pasa, rd_pasa,
                            fuga_falla, pat_falla, rd_falla)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (row["fecha"], row["hora"], row["fuga_pasa"],
                         row["pat_pasa"], row["rd_pasa"], row["fuga_falla"],
                         row["pat_falla"], row["rd_falla"]),
                    )
                    count += 1
                logger.info("Migrados %d registros de verificación.", count)
            except Exception as e:
                logger.warning("No se pudo migrar historial de verificación: %s", e)

            src.close()

        # --- Migrar historial FDL ---
        if fdl_db.exists():
            src = sqlite3.connect(str(fdl_db))
            src.row_factory = sqlite3.Row
            rows = src.execute("SELECT * FROM historial").fetchall()
            count = 0
            for row in rows:
                dest.execute(
                    """INSERT INTO historial_fdl
                       (marca, producto, serial, fecha, hora, tension, a_medida, fp,
                        w_medida, consumo, fuga_medida, fuga, cn_medido, cn,
                        pat_medida, pat, resistida)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["marca"], row["producto"], row["serial"],
                     row["fecha"], row["hora"], row["tension"],
                     row["A_medida"], row["fp"], row["W_medida"],
                     row["consumo"], row["fuga_medida"], row["fuga"],
                     row["cn_medido"], row["cn"], row["pat_medida"],
                     row["pat"], row["resistida"]),
                )
                count += 1
            logger.info("Migrados %d registros de historial FDL.", count)
            src.close()

        # --- Migrar historial consumo ---
        if consumo_db.exists():
            src = sqlite3.connect(str(consumo_db))
            src.row_factory = sqlite3.Row
            rows = src.execute("SELECT * FROM ensayos").fetchall()
            count = 0
            for row in rows:
                dest.execute(
                    """INSERT INTO ensayos_consumo
                       (n_ensayo, n_muestra, marca, modelo, nro_serial, fecha, hora,
                        tension, corriente, fp, potencia_ac, cdf)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["n_ensayo"], row["n_muestra"], row["marca"],
                     row["modelo"], row["nro_serial"], row["fecha"],
                     row["hora"], row["tension"], row["corriente"],
                     row["fp"], row["potencia_ac"], row["cdf"]),
                )
                count += 1
            logger.info("Migrados %d muestras de consumo.", count)
            src.close()

        dest.commit()
        logger.info("Migración completada exitosamente → %s", output_path)

    except Exception as e:
        dest.rollback()
        logger.error("Error durante la migración: %s", e)
        raise
    finally:
        dest.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrar datos de FDL (3 DBs) al nuevo esquema unificado."
    )
    parser.add_argument(
        "--fdl-dir",
        required=True,
        help="Directorio con las 3 bases de datos de FDL (database.db, historial_fdl.db, historial_consumo.db)",
    )
    parser.add_argument(
        "--output",
        default="data/ensayos.db",
        help="Ruta de la nueva base de datos unificada (default: data/ensayos.db)",
    )
    args = parser.parse_args()
    migrate(args.fdl_dir, args.output)


if __name__ == "__main__":
    main()
