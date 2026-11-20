"""Genera los esquemas de conexión de los ensayos de fuga activa, fuga pasiva y PAT.

Los esquemas siguen la asignación de relés de .env.example (RELAY_FUGA_ACTIVA=1,
RELAY_FUGA_PASIVA=2, RELAY_PAT_POWER=3, RELAY_PAT_ENABLE=7) y los circuitos de
IEC 60335-1: 13.2 (figura 2), 16.2 y Anexo A.1.

Uso: uv run --no-project --with matplotlib python gen_esquemas_ensayos.py <carpeta>
Genera PNG, PDF y SVG de cada esquema.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
plt.rcParams["font.family"] = "DejaVu Sans"

# Colores de conductores (convención IEC 60445) y de bloques
COL = {
    "L": "#8B4513",  # fase: marrón
    "N": "#1F5FBF",  # neutro: azul
    "PE": "#2E8B57",  # tierra: verde
    "MED": "#C0392B",  # circuito de medición
    "LV": "#D35400",  # baja tensión de PAT
    "CTRL": "#7F8C8D",  # control
}
FILL = {
    "red": "#F4C7A1",
    "trafo": "#FBE3C8",
    "med": "#F9D3CF",
    "dut": "#FFFFFF",
    "rele": "#C9E4C5",
    "nota": "#F7F7F7",
    "pend": "#FFF4CC",
}


def wire(ax, pts, color, lw=2.0, ls="-"):
    """Conductor como polilínea."""
    xs, ys = zip(*pts, strict=True)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle="round", zorder=2)


def dot(ax, x, y, color="#222222", r=0.06):
    """Punto de conexión."""
    ax.add_patch(Circle((x, y), r, fc=color, ec=color, zorder=5))


def block(ax, x, y, w, h, text, fill, fs=9, bold=False, dashed=False):
    """Bloque con texto centrado."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            fc=fill,
            ec="#333333",
            lw=1.2,
            ls="--" if dashed else "-",
            zorder=3,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        fontweight="bold" if bold else "normal",
        zorder=4,
    )


def switch(ax, x, y, color, closed=False, label="", label_dy=0.28, fs=8):
    """Contacto NA horizontal entre (x, y) y (x + 0.6, y)."""
    dot(ax, x, y, color)
    dot(ax, x + 0.6, y, color)
    if closed:
        wire(ax, [(x, y), (x + 0.6, y)], color)
    else:
        wire(ax, [(x, y), (x + 0.52, y + 0.28)], color)
    if label:
        ax.text(x + 0.3, y + label_dy, label, ha="center", va="bottom", fontsize=fs, zorder=4)


def changeover(ax, x, y, color, label="", fs=8):
    """Contacto inversor: común en (x, y), NC en (x + 0.6, y + 0.35), NA en (x + 0.6, y - 0.35).

    En reposo la lámina toca el NC.
    """
    dot(ax, x, y, color)
    dot(ax, x + 0.6, y + 0.35, color)
    dot(ax, x + 0.6, y - 0.35, color)
    wire(ax, [(x, y), (x + 0.55, y + 0.33)], color)
    ax.text(x + 0.75, y + 0.35, "NC", fontsize=7, va="center", zorder=4)
    ax.text(x + 0.75, y - 0.35, "NA", fontsize=7, va="center", zorder=4)
    if label:
        ax.text(x + 0.3, y + 0.55, label, ha="center", va="bottom", fontsize=fs, zorder=4)


def fuse(ax, x, y, color, label=""):
    """Fusible horizontal entre (x, y) y (x + 0.5, y)."""
    ax.add_patch(Rectangle((x, y - 0.1), 0.5, 0.2, fc="white", ec=color, lw=1.6, zorder=4))
    wire(ax, [(x, y), (x + 0.5, y)], color, lw=1.0)
    if label:
        ax.text(x + 0.25, y + 0.17, label, ha="center", va="bottom", fontsize=7.5, zorder=4)


def earth(ax, x, y):
    """Símbolo de tierra con el extremo superior en (x, y)."""
    for i, w in enumerate((0.3, 0.2, 0.1)):
        ax.plot([x - w / 2, x + w / 2], [y - 0.08 * i, y - 0.08 * i], color=COL["PE"], lw=1.6)


def notes(ax, x, y, w, h, title, lines, fill="nota", fs=8.2):
    """Recuadro de notas con título."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            fc=FILL[fill],
            ec="#999999",
            lw=1.0,
            zorder=3,
        )
    )
    ax.text(x + 0.15, y + h - 0.15, title, fontsize=9, fontweight="bold", va="top", zorder=4)
    ax.text(
        x + 0.15,
        y + h - 0.5,
        "\n".join(lines),
        fontsize=fs,
        va="top",
        zorder=4,
        linespacing=1.45,
    )


def legend(ax, x, y):
    """Leyenda de colores de conductores."""
    items = [
        ("Fase (L)", COL["L"]),
        ("Neutro (N)", COL["N"]),
        ("Tierra (PE)", COL["PE"]),
        ("Medición", COL["MED"]),
    ]
    for i, (t, c) in enumerate(items):
        ax.plot([x + i * 2.0, x + i * 2.0 + 0.45], [y, y], color=c, lw=2.5)
        ax.text(x + i * 2.0 + 0.55, y, t, fontsize=8, va="center")


def canvas(title, subtitle):
    """Lienzo con título."""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.text(0.3, 9.7, title, fontsize=15, fontweight="bold", va="top")
    ax.text(0.3, 9.25, subtitle, fontsize=9.5, va="top", color="#444444")
    return fig, ax


def save(fig, name):
    """Guarda en PNG, PDF y SVG."""
    for ext in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def source_chain(ax, label_adj):
    """Red, fusible, transformador de aislación y ajuste de tensión. Devuelve x de salida."""
    ax.text(0.35, 7.0, "Red\n220 V~", fontsize=9, fontweight="bold", va="center")
    wire(ax, [(0.9, 7.6), (1.5, 7.6)], COL["L"])
    wire(ax, [(0.9, 6.6), (2.6, 6.6)], COL["N"])
    ax.text(0.95, 7.72, "L", fontsize=8, color=COL["L"])
    ax.text(0.95, 6.72, "N", fontsize=8, color=COL["N"])
    fuse(ax, 1.5, 7.6, COL["L"], "F 1 A")
    wire(ax, [(2.0, 7.6), (2.6, 7.6)], COL["L"])
    block(ax, 2.6, 6.3, 1.5, 1.6, "T1\nTrafo de\naislación\n1:1", FILL["trafo"], 8.5, True)
    wire(ax, [(4.1, 7.6), (4.5, 7.6)], COL["L"])
    wire(ax, [(4.1, 6.6), (4.5, 6.6)], COL["N"])
    block(ax, 4.5, 6.3, 1.5, 1.6, label_adj, FILL["pend"], 7.5, dashed=True)
    wire(ax, [(6.0, 7.6), (6.4, 7.6)], COL["L"])
    wire(ax, [(6.0, 6.6), (6.4, 6.6)], COL["N"])
    ax.text(6.05, 7.72, "L'", fontsize=8, color=COL["L"])
    ax.text(6.05, 6.72, "N'", fontsize=8, color=COL["N"])
    return 6.4


def rl1_earth_switch(ax):
    """RL1: tierra del DUT a la PE de la instalación (NC) o a la red C (NA).

    Devuelve el punto donde termina la conexión NA (entrada derecha de la red C).
    """
    # PE del DUT al común, rodeando los contactos por arriba
    wire(
        ax, [(11.5, 5.0), (11.38, 5.0), (11.38, 5.9), (9.2, 5.9), (9.2, 5.0), (9.4, 5.0)], COL["PE"]
    )
    changeover(ax, 9.4, 5.0, COL["PE"])
    ax.text(10.3, 6.0, "RL1 — RELAY_FUGA_ACTIVA", fontsize=8, ha="center", va="bottom")
    # NC: a la PE de la instalación
    wire(ax, [(10.0, 5.35), (10.3, 5.35), (10.3, 1.2)], COL["PE"])
    # NA: a la red C
    wire(ax, [(10.0, 4.65), (10.0, 4.3), (9.3, 4.3)], COL["MED"])


def network_c(ax, x, y):
    """Red de medición C (IEC 60990, figura 4), entradas en (x, y+0.45) y (x+2.4, y+0.45)."""
    block(
        ax,
        x,
        y,
        2.4,
        0.9,
        "C: red de medición\nIEC 60990, figura 4\nI = U2 / 500 Ω",
        FILL["med"],
        8,
        True,
    )


def meter_pzem2(ax, x, y):
    """Bloque de lectura de la corriente de fuga."""
    block(
        ax,
        x,
        y,
        2.4,
        0.8,
        "PZEM2 (fuga)\nlee U2 en true RMS\n(acondicionamiento a definir)",
        FILL["pend"],
        7.5,
        dashed=True,
    )


# ---------------------------------------------------------------------------
# Fuga activa (13.2, figura 2)
# ---------------------------------------------------------------------------
def fuga_activa():
    fig, ax = canvas(
        "Esquema de conexión — fuga activa (IEC 60335-1, 13.2, figura 2)",
        "Aparato Clase I en funcionamiento; la tierra del aparato se separa de la tierra de "
        "protección y se lleva a la red de medición, que se cierra contra cada polo (a y b).",
    )
    x0 = source_chain(ax, "Ajuste de\nalimentación\n1,06·Un (motor)\n1,15·Pn (calef.)")

    # K1: alimentación del DUT
    wire(ax, [(x0, 7.6), (7.6, 7.6)], COL["L"])
    wire(ax, [(x0, 6.6), (7.6, 6.6)], COL["N"])
    switch(ax, 7.6, 7.6, COL["L"], closed=True, label="K1 (contactor)")
    switch(ax, 7.6, 6.6, COL["N"], closed=True)
    wire(ax, [(8.2, 7.6), (11.5, 7.6)], COL["L"])
    wire(ax, [(8.2, 6.6), (11.5, 6.6)], COL["N"])

    # DUT
    block(ax, 11.5, 4.6, 2.6, 3.4, "", FILL["dut"])
    ax.text(12.8, 7.75, "DUT", ha="center", fontsize=11, fontweight="bold", zorder=4)
    ax.text(
        12.8,
        6.0,
        "Clase I\nencendido, en\nfuncionamiento\n\nPartes metálicas\naccesibles + lámina\n"
        "≤ 20 × 10 cm",
        ha="center",
        va="center",
        fontsize=8,
        zorder=4,
    )
    for yy, t, c in ((7.6, "L", COL["L"]), (6.6, "N", COL["N"]), (5.0, "PE", COL["PE"])):
        dot(ax, 11.5, yy, c)
        ax.text(11.25, yy + 0.08, t, fontsize=7.5, color=c, ha="right")

    rl1_earth_switch(ax)
    network_c(ax, 6.9, 3.85)
    # Selector a/b
    wire(ax, [(6.9, 4.3), (6.2, 4.3)], COL["MED"])
    dot(ax, 6.2, 4.3, COL["MED"])
    dot(ax, 5.7, 4.8, COL["MED"])
    dot(ax, 6.7, 4.8, COL["MED"])
    wire(ax, [(6.2, 4.3), (5.75, 4.75)], COL["MED"])
    ax.text(5.55, 4.95, "a", fontsize=8.5, fontweight="bold")
    ax.text(6.75, 4.95, "b", fontsize=8.5, fontweight="bold")
    wire(ax, [(5.7, 4.8), (5.7, 6.0), (6.9, 6.0), (6.9, 7.6)], COL["MED"], lw=1.4)
    wire(ax, [(6.7, 4.8), (6.7, 5.6), (7.2, 5.6), (7.2, 6.6)], COL["MED"], lw=1.4)
    dot(ax, 6.9, 7.6, COL["L"])
    dot(ax, 7.2, 6.6, COL["N"])
    ax.text(
        4.7,
        5.1,
        "S a/b: selector\nde polaridad\n(relé adicional)",
        fontsize=7.5,
        ha="center",
        va="center",
    )

    meter_pzem2(ax, 6.9, 2.7)
    wire(ax, [(8.1, 3.85), (8.1, 3.5)], COL["MED"], ls="--", lw=1.3)

    # Tierra de protección
    wire(ax, [(0.9, 1.2), (10.3, 1.2)], COL["PE"])
    ax.text(0.95, 1.32, "PE de la instalación", fontsize=8, color=COL["PE"])
    earth(ax, 0.9, 1.2)

    notes(
        ax,
        12.0,
        0.4,
        3.9,
        3.9,
        "Secuencia del software",
        [
            "1. K1 cierra: el aparato funciona",
            "   (tiempo de 11.7 antes de medir).",
            "2. RL1 activa: PE del DUT → red C.",
            "3. Lectura de PZEM2 durante",
            "   TEST_ACTIVE_LEAKAGE_DURATION.",
            "4. RL1 vuelve a reposo (PE a tierra).",
            "",
            "Límite: 0,75 mA (Clase I portátil).",
        ],
    )
    notes(
        ax,
        0.3,
        2.0,
        3.6,
        2.3,
        "Pendiente / a definir",
        [
            "• S a/b: el software usa un solo",
            "  relé; falta medir en a y en b.",
            "• Ajuste 1,06·Un / 1,15·Pn: el",
            "  banco no tiene autotransformador.",
            "• PZEM 10 A resuelve 1 mA: no",
            "  alcanza para 0,75 mA sin etapa",
            "  de acondicionamiento.",
        ],
        fill="pend",
        fs=7.6,
    )
    legend(ax, 0.4, 0.45)
    save(fig, "conexion_fuga_activa")


# ---------------------------------------------------------------------------
# Fuga pasiva (16.2)
# ---------------------------------------------------------------------------
def fuga_pasiva():
    fig, ax = canvas(
        "Esquema de conexión — fuga pasiva (IEC 60335-1, 16.2)",
        "Aparato desconectado de la red (K1 abierto), con sus interruptores en encendido: "
        "se aplica 1,06·Un entre las partes activas (L y N unidas) y las partes metálicas.",
    )
    x0 = source_chain(ax, "Ajuste de\ntensión de\nensayo\n1,06·Un")

    # K1 abierto: el DUT no recibe la red
    wire(ax, [(x0, 7.6), (7.6, 7.6)], COL["L"])
    wire(ax, [(x0, 6.6), (7.6, 6.6)], COL["N"])
    switch(ax, 7.6, 7.6, COL["L"], closed=False, label="K1 abierto (enclavamiento)")
    switch(ax, 7.6, 6.6, COL["N"], closed=False)
    wire(ax, [(8.2, 7.6), (11.5, 7.6)], COL["L"])
    wire(ax, [(8.2, 6.6), (11.5, 6.6)], COL["N"])

    # DUT
    block(ax, 11.5, 4.6, 2.6, 3.4, "", FILL["dut"])
    ax.text(12.8, 7.75, "DUT", ha="center", fontsize=11, fontweight="bold", zorder=4)
    ax.text(
        12.8,
        6.0,
        "Clase I\nsin alimentar\ninterruptores en\nencendido\n\n"
        "Partes metálicas\n+ lámina ≤ 20 × 10 cm",
        ha="center",
        va="center",
        fontsize=8,
        zorder=4,
    )
    for yy, t, c in ((7.6, "L", COL["L"]), (6.6, "N", COL["N"]), (5.0, "PE", COL["PE"])):
        dot(ax, 11.5, yy, c)
        ax.text(11.25, yy + 0.08, t, fontsize=7.5, color=c, ha="right")

    # RL2a: une L y N del DUT (contacto vertical entre ambos conductores)
    dot(ax, 10.4, 7.6, COL["L"])
    dot(ax, 10.4, 6.6, COL["N"])
    wire(ax, [(10.4, 7.6), (10.4, 7.3)], COL["MED"])
    wire(ax, [(10.4, 6.6), (10.4, 6.9)], COL["MED"])
    dot(ax, 10.4, 7.3, COL["MED"])
    dot(ax, 10.4, 6.9, COL["MED"])
    wire(ax, [(10.4, 7.3), (10.4, 6.9)], COL["MED"])
    ax.text(10.3, 7.1, "RL2a: une\nL y N", fontsize=7.5, ha="right", va="center")
    # RL2b: lleva L+N del DUT a L' de la fuente de ensayo
    dot(ax, 10.9, 7.6, COL["L"])
    dot(ax, 6.25, 7.6, COL["L"])
    wire(ax, [(10.9, 7.6), (10.9, 8.6), (7.2, 8.6)], COL["MED"])
    switch(ax, 6.6, 8.6, COL["MED"], closed=True)
    wire(ax, [(6.6, 8.6), (6.25, 8.6), (6.25, 7.6)], COL["MED"])
    ax.text(6.9, 8.75, "RL2b: L+N del DUT → L'", fontsize=7.5, ha="center", va="bottom")
    ax.text(
        9.05,
        8.75,
        "RL2 — RELAY_FUGA_PASIVA (dos contactos)",
        fontsize=8,
        fontweight="bold",
        va="bottom",
    )

    rl1_earth_switch(ax)
    network_c(ax, 6.9, 3.85)
    wire(ax, [(6.9, 4.3), (6.5, 4.3), (6.5, 6.6)], COL["MED"])
    dot(ax, 6.5, 6.6, COL["N"])

    meter_pzem2(ax, 6.9, 2.7)
    wire(ax, [(8.1, 3.85), (8.1, 3.5)], COL["MED"], ls="--", lw=1.3)

    wire(ax, [(0.9, 1.2), (10.3, 1.2)], COL["PE"])
    ax.text(0.95, 1.32, "PE de la instalación", fontsize=8, color=COL["PE"])
    earth(ax, 0.9, 1.2)

    notes(
        ax,
        12.0,
        0.4,
        3.9,
        3.9,
        "Secuencia del software",
        [
            "1. K1 abierto (el DUT no recibe red).",
            "2. RL2 activa: L+N del DUT → L'.",
            "3. Espera RELAY_SETTLE_DELAY.",
            "4. RL1 activa: PE del DUT → red C.",
            "5. Lectura de PZEM2 (dentro de 5 s).",
            "6. Libera RL1 y después RL2.",
            "",
            "Límite: 0,75 mA (1,5 mA si duplica).",
        ],
    )
    notes(
        ax,
        0.3,
        2.0,
        3.6,
        2.3,
        "Pendiente / a definir",
        [
            "• RL2 necesita dos contactos (o",
            "  dos relés): puente L-N y salida",
            "  hacia L'.",
            "• K1 y RL2 deben enclavarse: nunca",
            "  cerrados a la vez.",
            "• Mismas limitaciones de medición",
            "  y de ajuste de tensión.",
        ],
        fill="pend",
        fs=7.6,
    )
    legend(ax, 0.4, 0.45)
    save(fig, "conexion_fuga_pasiva")


# ---------------------------------------------------------------------------
# Puesta a tierra (Anexo A.1)
# ---------------------------------------------------------------------------
def pat():
    fig, ax = canvas(
        "Esquema de conexión — puesta a tierra (IEC 60335-1, Anexo A.1)",
        "Al menos 10 A desde una fuente de no más de 12 V entre la espiga de tierra de la ficha "
        "y cada parte metálica accesible; se mide la caída de tensión y se calcula R = U / I.",
    )
    # Primario
    ax.text(0.35, 7.0, "Red\n220 V~", fontsize=9, fontweight="bold", va="center")
    wire(ax, [(0.9, 7.6), (1.5, 7.6)], COL["L"])
    wire(ax, [(0.9, 6.6), (4.3, 6.6)], COL["N"])
    ax.text(0.95, 7.72, "L", fontsize=8, color=COL["L"])
    ax.text(0.95, 6.72, "N", fontsize=8, color=COL["N"])
    fuse(ax, 1.5, 7.6, COL["L"], "F 1 A")
    wire(ax, [(2.0, 7.6), (2.6, 7.6)], COL["L"])
    switch(ax, 2.6, 7.6, COL["L"], closed=True, label="RL3 — RELAY_PAT_POWER")
    wire(ax, [(3.2, 7.6), (4.3, 7.6)], COL["L"])
    block(ax, 4.3, 6.2, 1.8, 1.8, "T2\n220 V / 2,2 V\n75 VA", FILL["trafo"], 9, True)

    # Secundario de baja tensión
    wire(ax, [(6.1, 7.6), (7.0, 7.6)], COL["LV"], lw=3.0)
    wire(ax, [(6.1, 6.6), (6.6, 6.6), (6.6, 3.0)], COL["LV"], lw=3.0)
    ax.text(6.2, 7.2, "2,2 V~\n≥ 10 A", fontsize=8, color=COL["LV"], va="top")
    block(ax, 7.0, 7.2, 1.7, 0.8, "K2 (contactor\n≥ 15 A)\nRELAY_PAT_ENABLE", FILL["rele"], 7.5)
    wire(ax, [(8.7, 7.6), (9.4, 7.6)], COL["LV"], lw=3.0)
    # TI del PZEM3
    ax.add_patch(Circle((9.7, 7.6), 0.3, fc="none", ec=COL["MED"], lw=2.0, zorder=4))
    ax.text(9.7, 8.05, "TI del PZEM3\n(corriente I)", fontsize=7.5, ha="center", color=COL["MED"])
    wire(ax, [(9.4, 7.6), (10.6, 7.6), (10.6, 5.3)], COL["LV"], lw=3.0)

    # Toma del banco y DUT
    block(ax, 10.1, 4.5, 1.0, 0.8, "Toma\nPE", FILL["dut"], 8)
    wire(ax, [(11.1, 4.9), (11.8, 4.9)], COL["PE"], lw=3.0)
    block(ax, 11.8, 2.6, 3.0, 3.0, "", FILL["dut"])
    ax.text(13.3, 5.3, "DUT", ha="center", fontsize=11, fontweight="bold", zorder=4)
    ax.text(
        13.3,
        3.9,
        "Clase I, desconectado\n(K1 abierto)\n\n"
        "espiga de tierra\n→ cable → parte\nmetálica accesible",
        ha="center",
        va="center",
        fontsize=8,
        zorder=4,
    )
    dot(ax, 11.8, 4.9, COL["PE"])
    ax.text(11.85, 5.05, "espiga PE", fontsize=7, color=COL["PE"])
    dot(ax, 14.8, 3.2, "#222222")
    ax.text(14.85, 3.35, "parte metálica", fontsize=7)

    # Punta de prueba (retorno)
    wire(ax, [(6.6, 3.0), (6.6, 1.9), (15.3, 1.9), (15.3, 3.2), (14.8, 3.2)], COL["LV"], lw=3.0)
    ax.text(15.35, 2.5, "punta de\nprueba", fontsize=7.5)

    # Medición a 4 hilos
    wire(ax, [(11.8, 4.75), (11.4, 4.75), (11.4, 3.6), (10.6, 3.6)], COL["MED"], lw=1.2, ls="--")
    wire(ax, [(14.8, 3.05), (14.5, 2.35), (10.6, 2.35), (10.6, 3.0)], COL["MED"], lw=1.2, ls="--")
    block(
        ax,
        8.0,
        2.9,
        2.6,
        1.0,
        "Medición de caída de\ntensión U a 4 hilos\n(acondicionamiento → PZEM3)",
        FILL["pend"],
        7.5,
        dashed=True,
    )

    notes(
        ax,
        0.3,
        0.6,
        5.6,
        4.6,
        "Secuencia del software",
        [
            "1. K1 abierto: el DUT no recibe red.",
            "2. Operario: punta de prueba en la",
            "   parte metálica accesible.",
            "3. RL3 activa: energiza el primario de T2.",
            "4. Espera RELAY_SETTLE_DELAY.",
            "5. RL7 activa K2: circula la corriente.",
            "6. PZEM3: I (TI) y U (4 hilos);",
            "   R = U / I (peor caso del intervalo).",
            "7. Libera K2 y después RL3.",
            "",
            "Límite: 200 mΩ con cable fijo; 100 mΩ sin cable.",
        ],
    )
    notes(
        ax,
        6.3,
        0.1,
        5.3,
        1.55,
        "Pendiente / a definir",
        [
            "• El PZEM mide tensión desde 80 V: la caída de ~2 V necesita otra",
            "  etapa (ADC aislado o divisor/amplificador); calibrar el factor.",
            "• Los relés del HW-554 son de 10 A: RL7 debe comandar un contactor.",
        ],
        fill="pend",
        fs=7.6,
    )
    ax.plot([12.2, 12.65], [8.55, 8.55], color=COL["LV"], lw=3.0)
    ax.text(12.75, 8.55, "Circuito de ensayo (2,2 V, ≥ 10 A)", fontsize=8, va="center")
    ax.plot([12.2, 12.65], [8.15, 8.15], color=COL["MED"], lw=1.2, ls="--")
    ax.text(12.75, 8.15, "Medición de tensión (4 hilos)", fontsize=8, va="center")
    save(fig, "conexion_pat")


fuga_activa()
fuga_pasiva()
pat()
print("ok")
