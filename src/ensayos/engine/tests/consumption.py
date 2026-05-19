"""Ensayo de consumo eléctrico."""

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_consumption
from ensayos.models.enums import TestType, Verdict
from ensayos.models.measurement import ConsumptionMeasurement, LeakageMeasurement


class ConsumptionTest(AbstractTest):
    """Ensayo de consumo: mide tensión, corriente, potencia y factor de potencia.

    Secuencia de relés (FDL): activa rele1_1 (fuga_activa)
    Lectura: PZEM1 (consumo). Si fuga activa incluida, también lee PZEM2.

    Opcionalmente mide fuga activa simultáneamente cuando ambos ensayos
    están seleccionados (optimización de FDL).
    """

    def __init__(
        self,
        *args,
        rated_current: float = 0.0,
        rated_power: float = 0.0,
        include_leakage: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.rated_current = rated_current
        self.rated_power = rated_power
        self.include_leakage = include_leakage
        self.last_leakage: LeakageMeasurement | None = None

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
            return consumption
        return self.hardware.read_consumption()

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        self.hardware.deactivate_relay(relay_map.fuga_activa)

    def evaluate(self, measurement: ConsumptionMeasurement) -> Verdict:
        verdict_current, verdict_power = evaluate_consumption(
            measured_current=measurement.current,
            rated_current=self.rated_current,
            measured_power=measurement.voltage * measurement.current,
            rated_power=self.rated_power,
        )
        if verdict_current == Verdict.OK and verdict_power == Verdict.OK:
            return Verdict.OK
        return Verdict.FAIL
