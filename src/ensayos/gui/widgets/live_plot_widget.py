"""Series de los gráficos en vivo de la pestaña Consumo.

El .ui declara los gráficos como ``pglive.sources.live_plot_widget.LivePlotWidget``,
que es un ``pyqtgraph.PlotWidget``. ``PlotSeries`` dibuja sobre ese widget una curva
que se completa punto a punto.
"""

import pyqtgraph as pg


class PlotSeries:
    """Curva de una magnitud en función del tiempo sobre un PlotWidget de pyqtgraph.

    Args:
        plot: Gráfico del .ui (un ``pyqtgraph.PlotWidget``).
        title: Nombre de la magnitud para el eje vertical (por ejemplo, "Potencia").
        units: Unidad (por ejemplo, "W").
    """

    def __init__(self, plot: pg.PlotWidget, title: str, units: str):
        self.plot = plot
        self._x: list[float] = []
        self._y: list[float] = []
        plot.setBackground("k")
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setLabel("bottom", "Tiempo", units="s")
        plot.setLabel("left", title, units=units)
        self._curve = plot.plot(
            [],
            [],
            pen=pg.mkPen("#2ecc71", width=2),
            symbol="o",
            symbolSize=5,
            symbolBrush="#2ecc71",
        )

    def add_point(self, x: float, y: float) -> None:
        """Agrega un punto al final de la curva."""
        self._x.append(x)
        self._y.append(y)
        self._curve.setData(self._x, self._y)

    def clear(self) -> None:
        """Borra la curva."""
        self._x.clear()
        self._y.clear()
        self._curve.setData([], [])

    def point_count(self) -> int:
        """Cantidad de puntos graficados."""
        return len(self._x)
