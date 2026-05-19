"""Exportación de historiales a Excel (.xlsx)."""

import logging
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

from ensayos.database.schemas import get_connection

logger = logging.getLogger(__name__)

HEADERS_FDL = [
    "N.º Ensayo", "Marca", "Modelo", "N.º Serie", "Fecha", "Hora",
    "Tensión (V)", "Corriente (A)", "FP", "Potencia (W)", "CONSUMO V.",
    "Fuga A. (μA)", "FUGA ACTIVA V.", "Fuga P. (μA)", "FUGA PASIVA V.",
    "R. de P. a T. (mΩ)", "P. A T. V.", "Rigidez Dieléctrica V.",
]

HEADERS_CONSUMO = [
    "N.º Ensayo", "N.º Muestra", "Marca", "Modelo", "N.º Serie",
    "Fecha", "Hora", "Tensión (V)", "Corriente (A)", "FP",
    "Potencia (W)", "Fuga Activa (μA)",
]

HEADERS_VERIFICACION = [
    "ID", "Fecha", "Hora", "FUGA-1", "PAT-1", "RD-1",
    "FUGA-2", "PAT-2", "RD-2",
]


def export_to_excel(
    output_path: str,
    fecha_desde: date,
    fecha_hasta: date,
    db_path: str | None = None,
) -> str:
    """Exporta los historiales a un archivo Excel con 3 hojas.

    Args:
        output_path: Ruta del archivo .xlsx de salida.
        fecha_desde: Fecha de inicio del filtro.
        fecha_hasta: Fecha de fin del filtro.
        db_path: Ruta de la DB (usa config si es None).

    Returns:
        Ruta absoluta del archivo generado.
    """
    wb = Workbook()

    # Hoja 1: FDL
    sheet_fdl = wb.active
    sheet_fdl.title = "FDL"
    sheet_fdl.append(HEADERS_FDL)

    # Hoja 2: CONSUMO
    sheet_consumo = wb.create_sheet("CONSUMO")
    sheet_consumo.append(HEADERS_CONSUMO)

    # Hoja 3: VERIFICACION
    sheet_verif = wb.create_sheet("VERIFICACION")
    sheet_verif.append(HEADERS_VERIFICACION)

    days = (fecha_hasta - fecha_desde).days

    with get_connection(db_path) as conn:
        for d in range(days + 1):
            date_str = (fecha_desde + timedelta(days=d)).strftime("%d/%m/%Y")

            # FDL
            rows = conn.execute(
                "SELECT * FROM historial_fdl WHERE fecha = ?", (date_str,)
            ).fetchall()
            for row in rows:
                sheet_fdl.append(list(row))

            # Consumo (omitir columna id)
            rows = conn.execute(
                "SELECT * FROM ensayos_consumo WHERE fecha = ?", (date_str,)
            ).fetchall()
            for row in rows:
                values = list(row)
                sheet_consumo.append(values[1:])  # omit id

            # Verificación
            rows = conn.execute(
                "SELECT * FROM historial_verificacion WHERE fecha = ?", (date_str,)
            ).fetchall()
            for row in rows:
                sheet_verif.append(list(row))

    # Guardar archivo
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output))

    logger.info("Excel exportado: %s", output.resolve())
    return str(output.resolve())


def export_to_desktop(
    fecha_desde: date,
    fecha_hasta: date,
    db_path: str | None = None,
    filename: str = "Historial.xlsx",
) -> str:
    """Exporta al escritorio del usuario."""
    desktop = Path.home() / "Escritorio"
    if not desktop.exists():
        desktop = Path.home() / "Desktop"
    output = desktop / filename
    return export_to_excel(str(output), fecha_desde, fecha_hasta, db_path)


def export_to_usb(
    fecha_desde: date,
    fecha_hasta: date,
    db_path: str | None = None,
    media_path: str = "/media",
    filename: str = "Historial.xlsx",
) -> str | None:
    """Exporta al primer dispositivo USB montado.

    Returns:
        Ruta del archivo generado o None si no hay USB.
    """
    import os

    user = os.environ.get("USER", "")
    base = Path(media_path) / user

    if not base.exists():
        logger.warning("No se encontró directorio de medios: %s", base)
        return None

    # Buscar primer directorio montado
    subdirs = [d for d in base.iterdir() if d.is_dir()]
    if not subdirs:
        logger.warning("No hay dispositivos USB montados en %s", base)
        return None

    output = subdirs[0] / filename
    return export_to_excel(str(output), fecha_desde, fecha_hasta, db_path)
