"""Tests del ensayo de perfil de consumo (ConsumptionProfile) con reloj simulado."""

from threading import Event
from types import SimpleNamespace

import pytest

from ensayos.engine.consumption_profile import ConsumptionProfile
from ensayos.models.enums import DeviceClass
from ensayos.models.measurement import ConsumptionMeasurement, LeakageMeasurement
from ensayos.models.product import Product

PRODUCT = Product(
    marca="Bancolab",
    modelo="Soldador",
    descripcion="",
    potencia=40,
    tension=220,
    corriente=0.18,
    frecuencia=50,
    clase=DeviceClass.CLASS_1,
)


class FakeClock:
    """Reloj simulado: sleep() avanza el tiempo al instante."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeHardware:
    def __init__(self, consumption=None, leakage=None, cancel_after=None):
        self._cfg = SimpleNamespace(relay=SimpleNamespace(mapping=SimpleNamespace(fuga_activa=1)))
        self.relay_log: list[str] = []
        self._consumption = consumption
        self._leakage = leakage
        self.reads = 0
        self.cancel_after = cancel_after
        self.profile = None

    def activate_relay(self, n):
        self.relay_log.append(f"on{n}")

    def deactivate_relay(self, n):
        self.relay_log.append(f"off{n}")

    def read_consumption(self):
        self.reads += 1
        if self.cancel_after and self.reads >= self.cancel_after:
            self.profile.stop()
        if callable(self._consumption):
            return self._consumption(self.reads)
        return self._consumption

    def read_leakage(self, watchdog=True):
        assert watchdog is False  # en el perfil la fuga es opcional
        return self._leakage


def make(hw, duration=20, interval=5, settle=2, **kw):
    clock = FakeClock()
    p = ConsumptionProfile(
        hw,
        PRODUCT,
        "SN1",
        test_number=7,
        duration_s=duration,
        interval_s=interval,
        settle_s=settle,
        sleep=clock.sleep,
        clock=clock,
        **kw,
    )
    hw.profile = p
    return p, clock


def test_toma_una_muestra_por_intervalo_y_abre_el_contactor():
    hw = FakeHardware(consumption=ConsumptionMeasurement(230.0, 0.16, 37.6, 1.0))
    p, clock = make(hw, duration=20, interval=5, settle=2)
    samples = p.run()
    # Muestras en t = 0, 5, 10, 15 y 20 s (tras 2 s de estabilización)
    assert [s.n_muestra for s in samples] == [1, 2, 3, 4, 5]
    assert all(s.n_ensayo == 7 and s.serial == "SN1" for s in samples)
    assert samples[0].potencia == 37.6 and samples[0].fuga_activa == 0.0
    assert hw.relay_log == ["on1", "off1"]
    assert clock.now == pytest.approx(22.0, abs=0.2)


def test_guarda_la_fuga_si_hay_pzem2():
    hw = FakeHardware(ConsumptionMeasurement(230.0, 0.16, 37.6, 1.0), LeakageMeasurement(123.4))
    p, _ = make(hw, duration=5, interval=5)
    assert all(s.fuga_activa == 123.4 for s in p.run())


def test_lectura_fallida_se_saltea():
    lectura = ConsumptionMeasurement(230.0, 0.16, 37.6, 1.0)
    hw = FakeHardware(consumption=lambda n: None if n == 2 else lectura)
    p, _ = make(hw, duration=10, interval=5)
    samples = p.run()
    assert [s.n_muestra for s in samples] == [1, 3]
    assert p.missed_samples == 1


def test_parada_corta_y_abre_el_contactor():
    hw = FakeHardware(ConsumptionMeasurement(230.0, 0.16, 37.6, 1.0), cancel_after=2)
    p, clock = make(hw, duration=60, interval=5)
    samples = p.run()
    assert len(samples) == 2
    assert hw.relay_log == ["on1", "off1"]
    assert clock.now < 10


def test_error_de_lectura_abre_el_contactor():
    def falla(_n):
        raise OSError("ESP32 desconectada")

    hw = FakeHardware(consumption=falla)
    p, _ = make(hw)
    with pytest.raises(OSError):
        p.run()
    assert hw.relay_log == ["on1", "off1"]


def test_cuentas_regresivas():
    ticks = []
    hw = FakeHardware(ConsumptionMeasurement(230.0, 0.16, 37.6, 1.0))
    p, _ = make(hw, duration=10, interval=5, on_tick=ticks.append)
    p.run()
    assert ticks[0].seconds_to_next_sample == pytest.approx(5.0, abs=0.2)
    assert ticks[0].seconds_to_end == pytest.approx(10.0, abs=0.2)
    assert min(t.seconds_to_end for t in ticks) <= 1.0


@pytest.mark.parametrize("duration,interval", [(10, 0), (3, 5)])
def test_tiempos_invalidos(duration, interval):
    with pytest.raises(ValueError):
        ConsumptionProfile(FakeHardware(), PRODUCT, "", 1, duration, interval, cancel_token=Event())
