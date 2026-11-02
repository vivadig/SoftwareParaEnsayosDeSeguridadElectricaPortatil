"""Tests de compatibilidad entre ESP32Client y las respuestas del firmware."""

from ensayos.hardware.esp32_client import ESP32Client


class FakeSerial:
    """Puerto serie simulado que responde como firmware/esp32_pzem."""

    def __init__(self, responses: dict[str, str]):
        self._responses = responses
        self._pending: list[bytes] = []
        self.written: list[str] = []
        self.is_open = True

    @property
    def in_waiting(self) -> int:
        return sum(len(line) for line in self._pending)

    def reset_input_buffer(self) -> None:
        self._pending.clear()

    def write(self, data: bytes) -> int:
        command = data.decode().strip()
        self.written.append(command)
        if command in self._responses:
            self._pending.append((self._responses[command] + "\r\n").encode())
        return len(data)

    def readline(self) -> bytes:
        return self._pending.pop(0) if self._pending else b""

    def close(self) -> None:
        self.is_open = False


def make_client(responses: dict[str, str]) -> ESP32Client:
    client = ESP32Client(timeout=1)
    client.ser = FakeSerial(responses)
    client.is_connected = True
    return client


def test_lectura_valida_del_firmware():
    client = make_client({"PZEM1": "PZEM1:V=220.50,C=0.453,P=99.80,E=1.234,FP=0.98"})
    reading = client.read_pzem(1)
    assert reading is not None
    assert reading.voltage == 220.50
    assert reading.current == 0.453
    assert reading.power == 99.80
    assert reading.energy == 1.234
    assert reading.power_factor == 0.98


def test_pzem_sin_respuesta_devuelve_none():
    client = make_client({"PZEM2": "PZEM2:ERROR"})
    assert client.read_pzem(2) is None


def test_respuesta_de_otro_pzem_se_rechaza():
    client = make_client({"PZEM1": "PZEM3:V=1,C=1,P=1,E=1,FP=1"})
    assert client.read_pzem(1) is None


def test_relay_on_off():
    client = make_client({"RELAYON1": "RELE1_ON", "RELAYOFF1": "RELE1_OFF"})
    assert client.relay_on(1)
    assert client.relay_off(1)


def test_relay_inexistente():
    client = make_client({"RELAYON1": "RELE1_ERROR"})
    assert not client.relay_on(1)
