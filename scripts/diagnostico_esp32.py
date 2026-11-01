#!/usr/bin/env python3
"""Diagnóstico de conexión con el ESP32.

Lista los puertos serie del sistema, indica cuál reconocería el programa como ESP32
(con las mismas palabras clave que ``ESP32Client.find_port``) y, opcionalmente,
abre el puerto para ver si el firmware responde.

Uso:
    uv run python scripts/diagnostico_esp32.py              # solo detección
    uv run python scripts/diagnostico_esp32.py --escuchar   # muestra lo que imprime al arrancar
    uv run python scripts/diagnostico_esp32.py --pzem 1     # pide una lectura al PZEM1

El script nunca envía comandos de relé: solo lectura.
"""

import argparse
import sys
import time
from pathlib import Path

# Permite importar el paquete sin instalarlo (pyproject todavía empaqueta "src")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import serial  # noqa: E402
from serial.tools import list_ports  # noqa: E402
from serial.tools.list_ports_common import ListPortInfo  # noqa: E402

from ensayos.config.config_hardware import hardware_config  # noqa: E402
from ensayos.hardware.esp32_client import ESP32Client  # noqa: E402

# Chips USB-serie habituales en placas ESP32, por (VID, PID)
CHIPS_CONOCIDOS: dict[tuple[int, int], str] = {
    (0x10C4, 0xEA60): "Silicon Labs CP210x",
    (0x1A86, 0x7523): "WCH CH340",
    (0x1A86, 0x55D4): "WCH CH9102",
    (0x0403, 0x6001): "FTDI FT232",
    (0x303A, 0x1001): "USB nativo de ESP32-S2/S3/C3",
}


def describir_puerto(port: ListPortInfo, keywords: list[str]) -> str:
    """Arma una línea legible con los datos de un puerto serie.

    Args:
        port: Puerto devuelto por ``list_ports.comports()``.
        keywords: Palabras clave con las que el programa detecta el ESP32.

    Returns:
        Descripción del puerto, con el chip identificado y si el programa lo reconoce.
    """
    chip = ""
    if port.vid is not None and port.pid is not None:
        nombre = CHIPS_CONOCIDOS.get((port.vid, port.pid), "desconocido")
        chip = f" | VID:PID {port.vid:04X}:{port.pid:04X} ({nombre})"
    reconocido = any(k in port.description for k in keywords)
    marca = "SÍ" if reconocido else "no"
    return f"{port.device}: {port.description}{chip} | reconocido por el programa: {marca}"


def escuchar(puerto: str, segundos: float) -> None:
    """Abre el puerto y muestra todo lo que el ESP32 imprime durante un tiempo.

    Abrir el puerto reinicia la mayoría de las placas ESP32 (líneas DTR/RTS),
    así que se ve el arranque del firmware.

    Args:
        puerto: Puerto serie a abrir.
        segundos: Tiempo de escucha.
    """
    baud = hardware_config.esp32.baud_rate
    print(f"\nEscuchando {puerto} a {baud} baudios durante {segundos:.0f} s...")
    with serial.Serial(puerto, baud, timeout=0.5) as ser:
        fin = time.time() + segundos
        recibido = False
        while time.time() < fin:
            linea = ser.readline()
            if linea:
                recibido = True
                print("  <", linea.decode("utf-8", errors="replace").rstrip())
    if not recibido:
        print("  (no llegó nada: el firmware puede no imprimir al arrancar)")


def leer_pzem(pzem_id: int) -> bool:
    """Conecta con el cliente del programa y pide una lectura a un PZEM.

    Args:
        pzem_id: Número de PZEM (1: consumo, 2: fuga/dieléctrico, 3: puesta a tierra).

    Returns:
        True si el firmware respondió con una lectura válida.
    """
    client = ESP32Client()
    try:
        client.connect()
    except ConnectionError as e:
        print(f"\nNo se pudo conectar: {e}")
        return False
    try:
        respuesta = client.send_command(f"PZEM{pzem_id}")
        print(f"\nComando PZEM{pzem_id} -> respuesta cruda: {respuesta!r}")
        lectura = client.read_pzem(pzem_id)
        if lectura is None:
            print("Lectura inválida: el firmware no responde con el formato esperado")
            print(f"  (se espera 'PZEM{pzem_id}:V=...,C=...,P=...,E=...')")
            return False
        print(f"Lectura interpretada: {lectura}")
        return True
    finally:
        client.disconnect()


def main() -> int:
    """Punto de entrada del diagnóstico.

    Returns:
        Código de salida: 0 si se encontró el ESP32 (y respondió, si se pidió), 1 si no.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--escuchar",
        type=float,
        nargs="?",
        const=5.0,
        metavar="SEG",
        help="mostrar lo que imprime el ESP32 durante SEG segundos (5 por defecto)",
    )
    parser.add_argument("--pzem", type=int, metavar="N", help="pedir una lectura al PZEM N")
    args = parser.parse_args()

    keywords = hardware_config.esp32.port_keywords
    print(f"Palabras clave de detección (ESP32_PORT_KEYWORDS): {keywords}")
    puertos = sorted(list_ports.comports(), key=lambda p: p.device)
    if not puertos:
        print("No hay ningún puerto serie. ¿Está conectado el cable? ¿Es un cable solo de carga?")
        return 1
    print("\nPuertos serie encontrados:")
    for port in puertos:
        print("  " + describir_puerto(port, keywords))

    puerto = ESP32Client().find_port()
    if puerto is None:
        print("\nEl programa NO reconoce ningún puerto como ESP32.")
        print("Si la placa aparece arriba con otro nombre (por ejemplo CH340), agregá esa palabra")
        print("a ESP32_PORT_KEYWORDS en el archivo .env.")
        return 1
    print(f"\nEl programa usaría el puerto {puerto}.")

    if args.escuchar:
        escuchar(puerto, args.escuchar)
    if args.pzem is not None:
        return 0 if leer_pzem(args.pzem) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
