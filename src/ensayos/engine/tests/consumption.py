"""Ensayo de consumo eléctrico."""

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_consumption
from ensayos.models.enums import ApplianceType, TestType, Verdict
from ensayos.models.measurement import ConsumptionMeasurement, LeakageMeasurement


class ConsumptionTest(AbstractTest):
    """Ensayo de consumo: mide tensión, corriente, potencia y factor de potencia.

    Secuencia de relés (FDL): activa rele1_1 (fuga_activa)
    Lectura: PZEM1 (consumo). Si fuga activa incluida, también lee PZEM2.

    Opcionalmente mide fuga activa simultáneamente cuando ambos ensayos
    están seleccionados (optimización de FDL).

    Se evalúa el promedio del intervalo (IEC 60335-1, 10.1: si el consumo varía,
    se toma el valor medio durante un período representativo).
    """

    def __init__(
        self,
        *args,
        rated_current: float = 0.0,
        rated_power: float = 0.0,
        include_leakage: bool = False,
        appliance_type: ApplianceType = ApplianceType.HEATING,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.rated_current = rated_current
        self.rated_power = rated_power
        self.include_leakage = include_leakage
        self.appliance_type = appliance_type
        self.last_leakage: LeakageMeasurement | None = None
        self._samples: list[ConsumptionMeasurement] = []

    @property
    def test_type(self) -> TestType:
        return TestType.CONSUMPTION

    @property
    def duration_seconds(self) -> int:
        return self.config.durations.consumption

    def setup(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        self.hardware.activate_relay(relay_map.fuga_activa)

    def measure(self) -> ConsumptionMeasurement | None:
        if self.include_leakage:
            consumption, leakage = self.hardware.read_consumption_and_leakage()
            if leakage is not None:
                self.last_leakage = leakage
        else:
            consumption = self.hardware.read_consumption()
        if consumption is not None:
            self._samples.append(consumption)
        return consumption

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        self.hardware.deactivate_relay(relay_map.fuga_activa)

    def final_measurement(self) -> ConsumptionMeasurement | None:
        """Promedio de las lecturas del intervalo."""
        if not self._samples:
            return None
        n = len(self._samples)
        return ConsumptionMeasurement(
            voltage=sum(s.voltage for s in self._samples) / n,
            current=sum(s.current for s in self._samples) / n,
            power=sum(s.power for s in self._samples) / n,
            power_factor=sum(s.power_factor for s in self._samples) / n,
        )

    def evaluate(self, measurement: ConsumptionMeasurement) -> Verdict:
        # Potencia activa (W) del PZEM, no la aparente V × I
        return evaluate_consumption(
            measured_current=measurement.current,
            rated_current=self.rated_current,
            measured_power=measurement.power,
            rated_power=self.rated_power,
            appliance_type=self.appliance_type,
        )
