#!/usr/bin/env python3
"""Diagnóstico de la placa de relés USB con el mismo controlador que usa el programa.

Lista las placas, su número de serie y el estado de cada relé y, con ``--probar``,
enciende y apaga cada canal verificando el estado que informa la placa. Usa el
backend configurado en ``RELAY_BACKEND`` (``hidapi`` por defecto).

Uso:
    uv run python scripts/diagnostico_rele.py            # solo lectura
    uv run python scripts/diagnostico_rele.py --probar   # conmuta cada relé 1 s

ATENCIÓN: antes de usar ``--probar``, verificar que no haya ninguna carga ni
tensión de red conectada a los contactos de los relés.
"""

import argparse
import sys
import time
from pathlib import Path

# Permite importar el paquete sin instalarlo (pyproject todavía empaqueta "src")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ensayos.hardware.relay_controller import RelayController  # noqa: E402


def formatear_estado(state: int, relay_count: int) -> str:
    """Convierte la máscara de estado en texto legible.

    Args:
        state: Máscara de bits del estado (bit 0 = relé 1).
        relay_count: Cantidad de relés de la placa.

    Returns:
        Texto del tipo ``"R1=OFF R2=ON"``.
    """
    return " ".join(
        f"R{i}={'ON' if state >> (i - 1) & 1 else 'OFF'}" for i in range(1, relay_count + 1)
    )


def probar(controller: RelayController, serial: str, segundos: float) -> bool:
    """Enciende y apaga cada relé verificando el estado informado por la placa.

    Args:
        controller: Controlador de relés.
        serial: Serie de la placa a probar.
        segundos: Tiempo que permanece encendido cada relé.

    Returns:
        True si todos los relés respondieron como se esperaba.
    """
    count = controller.relay_count(serial)
    ok = True
    try:
        for relay in range(1, count + 1):
            controller.turn_on(serial, relay)
            time.sleep(0.1)
            encendido = controller.get_state(serial)
            print(f"  Relé {relay} ON  -> {formatear_estado(encendido or 0, count)}")
            time.sleep(segundos)
            controller.turn_off(serial, relay)
            time.sleep(0.1)
            apagado = controller.get_state(serial)
            print(f"  Relé {relay} OFF -> {formatear_estado(apagado or 0, count)}")
            if encendido != 1 << (relay - 1) or apagado != 0:
                print(f"  ¡El relé {relay} no informó el estado esperado!")
                ok = False
    finally:
        # Ante cualquier error, dejar todo apagado
        if not controller.turn_off_all(serial):
            print("  ¡ATENCIÓN! No se pudo confirmar que los relés quedaron apagados.")
            ok = False
    return ok


def main() -> int:
    """Punto de entrada del diagnóstico.

    Returns:
        Código de salida: 0 si se encontró al menos una placa (y la prueba pasó), 1 si no.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--probar",
        type=float,
        nargs="?",
        const=1.0,
        metavar="SEG",
        help="encender cada relé SEG segundos (1 por defecto) y verificar el estado",
    )
    args = parser.parse_args()

    controller = RelayController()
    placas = controller.get_boards()
    if not placas:
        print("No se encontró ninguna placa de relés USB (VID 16C0, PID 05DF).")
        return 1

    resultado = 0
    for serial, count, state in placas:
        print(f"Placa serie {serial}: {count} relés, estado {formatear_estado(state, count)}")
        if args.probar:
            print("Probando relés:")
            if not probar(controller, serial, args.probar):
                resultado = 1
    return resultado


if __name__ == "__main__":
    sys.exit(main())
