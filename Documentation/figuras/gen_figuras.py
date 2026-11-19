"""Genera las figuras de arquitectura y los diagramas de Gantt del informe."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(sys.argv[1])
plt.rcParams["font.family"] = "DejaVu Sans"

# Paleta sobria, legible en impresión
C = {
    "potencia": "#F4C7A1",
    "adq": "#BFD7EA",
    "control": "#C9E4C5",
    "com": "#E2D4F0",
    "seg": "#F2B8B5",
    "ext": "#E6E6E6",
    "edge": "#333333",
}


def box(ax, x, y, w, h, text, color, fs=10, bold=False):
    """Dibuja un bloque con texto centrado (coordenadas de la esquina inferior izquierda)."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            fc=color,
            ec=C["edge"],
            lw=1.2,
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
        wrap=True,
    )
    return (x, y, w, h)


def group(ax, x, y, w, h, title, color):
    """Dibuja un recuadro de agrupación con título arriba a la izquierda."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.2",
            fc=color,
            ec=C["edge"],
            lw=1.0,
            ls="--",
            alpha=0.35,
        )
    )
    ax.text(x + 0.12, y + h - 0.12, title, ha="left", va="top", fontsize=10.5, fontweight="bold")


def arrow(ax, p, q, label="", both=False, color="#333333", ls="-", fs=8.5, off=(0, 0.12)):
    """Flecha de p a q con etiqueta en el punto medio."""
    ax.add_patch(
        FancyArrowPatch(
            p,
            q,
            arrowstyle="<|-|>" if both else "-|>",
            mutation_scale=12,
            lw=1.3,
            color=color,
            ls=ls,
            shrinkA=2,
            shrinkB=2,
        )
    )
    if label:
        mx, my = (p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1]
        ax.text(
            mx,
            my,
            label,
            ha="center",
            va="bottom",
            fontsize=fs,
            bbox={"fc": "white", "ec": "none", "pad": 1.0},
        )


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


# ---------------------------------------------------------------------------
# Arquitectura del dispositivo
# ---------------------------------------------------------------------------
def arquitectura_dispositivo():
    fig, ax = canvas(14, 9)

    # PC
    box(ax, 0.4, 6.9, 2.6, 1.5, "PC\nInterfaz (software)\nPython / PyQt5", C["ext"], 10, True)

    # Comunicación
    group(ax, 3.6, 6.3, 3.4, 2.4, "Comunicación", C["com"])
    box(ax, 3.85, 7.45, 2.9, 0.75, "USB-serie (CP2102)\n115200 baud, texto", C["com"], 9)
    box(ax, 3.85, 6.5, 2.9, 0.75, "USB HID\n(lectura de estado)", C["com"], 9)

    # Control
    group(ax, 7.6, 6.3, 3.0, 2.4, "Control", C["control"])
    box(ax, 7.85, 7.45, 2.5, 0.75, "ESP32\n(firmware propio)", C["control"], 9.5, True)
    box(ax, 7.85, 6.5, 2.5, 0.75, "Placa de relés USB\n(HW-554, 8 canales)", C["control"], 9)

    # Adquisición
    group(ax, 11.1, 4.6, 2.6, 4.1, "Adquisición", C["adq"])
    box(ax, 11.3, 7.5, 2.2, 0.75, "PZEM 1\nConsumo", C["adq"], 9)
    box(ax, 11.3, 6.4, 2.2, 0.75, "PZEM 2\nFuga / rigidez", C["adq"], 9)
    box(ax, 11.3, 5.3, 2.2, 0.75, "PZEM 3\nPuesta a tierra", C["adq"], 9)

    # Potencia
    group(ax, 3.6, 1.0, 7.0, 4.6, "Potencia", C["potencia"])
    box(ax, 3.85, 3.9, 2.0, 1.0, "Red\n220 V / 50 Hz", C["potencia"], 9.5)
    box(ax, 6.15, 3.9, 2.0, 1.0, "Contactores\n(bobina 220 V\n+ varistor)", C["potencia"], 9)
    box(ax, 8.45, 3.9, 1.95, 1.0, "Trafo rigidez\n1000 / 2500 V", C["potencia"], 9)
    box(ax, 8.45, 2.45, 1.95, 1.0, "Trafo PAT\n2,2 V / 75 VA", C["potencia"], 9)
    box(ax, 6.15, 1.3, 2.0, 1.0, "DUT\n(aparato bajo\nensayo)", "#FFFFFF", 9.5, True)

    # Seguridad
    group(ax, 0.4, 1.0, 2.8, 4.6, "Seguridad", C["seg"])
    for i, t in enumerate(
        [
            "Fusibles\n1 A y 10 A",
            "Tierra de protección\ndirecta al DUT",
            "Indicadores",
            "Paro de\nemergencia",
        ]
    ):
        box(ax, 0.6, 4.35 - i * 1.0, 2.4, 0.8, t, C["seg"], 9)

    # Enlaces
    arrow(ax, (3.0, 7.83), (3.85, 7.83), both=True)
    arrow(ax, (3.0, 7.2), (3.85, 6.88), both=True)
    arrow(ax, (6.75, 7.83), (7.85, 7.83), both=True)
    arrow(ax, (6.75, 6.88), (7.85, 6.88), both=True)
    arrow(ax, (10.35, 7.83), (11.3, 7.83), both=True)
    arrow(ax, (10.35, 7.7), (11.3, 6.78), both=True)
    arrow(ax, (10.35, 7.6), (11.3, 5.68), both=True)
    ax.text(12.4, 4.95, "Bus UART2\nModbus RTU, 9600 baud", ha="center", fontsize=8.5)
    arrow(ax, (9.1, 6.5), (7.15, 4.9), "comando de bobinas", off=(0.25, 0.05))
    arrow(ax, (5.85, 4.4), (6.15, 4.4))
    arrow(ax, (8.15, 4.4), (8.45, 4.4))
    arrow(ax, (8.15, 4.1), (8.45, 2.95))
    arrow(ax, (7.15, 3.9), (7.15, 2.3), "alimentación\n(consumo, fuga)", off=(-0.75, -0.3))
    # salidas de los transformadores al DUT
    ax.plot([10.4, 10.5, 10.5], [4.4, 4.4, 1.6], color="#333333", lw=1.3)
    ax.plot([10.4, 10.5], [2.95, 2.95], color="#333333", lw=1.3)
    arrow(ax, (10.5, 1.6), (8.15, 1.6), "tensión de ensayo", off=(0, 0.05))
    arrow(ax, (11.8, 4.6), (10.45, 5.45), "medición de V, I, P, FP", ls="--", off=(0.55, -0.45))
    ax.text(
        7.0,
        0.35,
        "Placa de relés: HW-554 de 8 canales en el diseño final; en el banco se usó una "
        "placa USB HID de 2 canales.",
        ha="center",
        fontsize=8.5,
        style="italic",
    )
    fig.savefig(OUT / "arquitectura_dispositivo.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Arquitectura de la interfaz (software)
# ---------------------------------------------------------------------------
def arquitectura_interfaz():
    fig, ax = canvas(14, 9.6)

    # Capa de presentación
    group(ax, 0.3, 7.0, 13.4, 2.3, "Presentación", C["com"])
    tabs = [
        "Ensayos",
        "Productos",
        "Consumo",
        "Configura-\nciones",
        "Verificación",
        "Exportar",
        "Historial",
        "Administra-\nción",
    ]
    for i, t in enumerate(tabs):
        box(ax, 0.55 + i * 1.12, 7.25, 1.02, 0.95, t, "#FFFFFF", 8)
    ax.text(
        5.0,
        8.55,
        "Interfaz gráfica PyQt5 (login, gráficos en vivo)",
        ha="center",
        fontsize=9.5,
        fontweight="bold",
    )
    box(
        ax,
        9.75,
        7.25,
        3.7,
        1.55,
        "API REST (FastAPI)\nautenticación PBKDF2\n+ frontend web",
        "#FFFFFF",
        9,
    )

    # Motor
    group(ax, 0.3, 3.9, 6.6, 2.7, "Motor de ensayos", C["control"])
    box(
        ax,
        0.55,
        5.1,
        2.6,
        0.95,
        "TestRunner\nfinal de línea / cíclico\n/ verificación",
        "#FFFFFF",
        8.5,
        True,
    )
    box(
        ax,
        3.45,
        5.1,
        3.2,
        0.95,
        "Ensayos (Template Method)\nsetup → measure →\nteardown → evaluate",
        "#FFFFFF",
        8.5,
    )
    box(ax, 0.55, 4.1, 2.6, 0.75, "Veredictos\n(funciones puras)", "#FFFFFF", 8.5)
    box(
        ax,
        3.45,
        4.1,
        3.2,
        0.75,
        "Consumo, fuga activa/pasiva,\nPAT, rigidez dieléctrica",
        "#FFFFFF",
        8,
    )

    # Datos
    group(ax, 7.3, 3.9, 6.4, 2.7, "Datos y salidas", C["adq"])
    box(ax, 7.55, 5.1, 2.8, 0.95, "Modelos\nproducto, medición,\nresultado", "#FFFFFF", 8.5)
    box(ax, 10.65, 5.1, 2.8, 0.95, "Repositorio SQLite\nmigración de esquema", "#FFFFFF", 8.5)
    box(ax, 7.55, 4.1, 2.8, 0.75, "Exportación\nExcel / correo", "#FFFFFF", 8.5)
    box(ax, 10.65, 4.1, 2.8, 0.75, "Base ensayos.db", "#FFFFFF", 8.5)

    # Hardware
    group(ax, 0.3, 0.9, 8.6, 2.6, "Acceso al hardware", C["potencia"])
    box(
        ax,
        2.6,
        2.35,
        4.0,
        0.8,
        "HardwareManager (fachada)\nbloqueo, correcciones de calibración",
        "#FFFFFF",
        8.5,
        True,
    )
    box(ax, 0.55, 1.1, 3.6, 0.85, "Esp32Client\nserie, auto-detección,\nreconexión", "#FFFFFF", 8.5)
    box(
        ax,
        4.95,
        1.1,
        3.7,
        0.85,
        "RelayController\nhidapi / usbrelay,\nconfirmación de estado",
        "#FFFFFF",
        8.5,
    )

    # Configuración
    group(ax, 9.3, 0.9, 4.4, 2.6, "Configuración", C["ext"])
    box(ax, 9.55, 2.2, 3.9, 0.85, "Archivo .env\numbrales, correcciones, relés", "#FFFFFF", 8.5)
    box(ax, 9.55, 1.1, 3.9, 0.85, "Tabla «tiempos»\nduraciones (editable en GUI)", "#FFFFFF", 8.5)

    # Externos
    ax.text(2.35, 0.45, "ESP32 + PZEM", ha="center", fontsize=9, fontweight="bold")
    ax.text(6.8, 0.45, "Placa de relés USB", ha="center", fontsize=9, fontweight="bold")

    arrow(ax, (4.0, 7.25), (2.95, 6.05))
    arrow(ax, (11.6, 7.25), (12.05, 6.05), "historial")
    arrow(ax, (3.15, 5.57), (3.45, 5.57))
    arrow(ax, (1.85, 5.1), (1.85, 4.85))
    arrow(ax, (5.05, 5.1), (5.05, 4.85))
    arrow(ax, (6.65, 5.57), (7.55, 5.57), "resultados")
    arrow(ax, (10.35, 5.57), (10.65, 5.57))
    arrow(ax, (12.05, 5.1), (12.05, 4.85))
    arrow(ax, (10.65, 4.47), (10.35, 4.47))
    arrow(ax, (5.05, 4.1), (4.6, 3.15), "lecturas y relés", off=(-0.6, 0.0))
    arrow(ax, (3.6, 2.35), (2.35, 1.95))
    arrow(ax, (5.6, 2.35), (6.8, 1.95))
    arrow(ax, (2.35, 1.1), (2.35, 0.7), both=True)
    arrow(ax, (6.8, 1.1), (6.8, 0.7), both=True)
    arrow(ax, (9.55, 2.62), (6.6, 2.75), ls="--")
    arrow(ax, (13.3, 3.05), (6.65, 4.1), "parámetros", ls="--", off=(0, 0.05))

    fig.savefig(OUT / "arquitectura_interfaz.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Diagramas de Gantt
# ---------------------------------------------------------------------------
HW = [
    (
        "1. Diseño inicial del sistema",
        [
            ("Relevamiento y ubicación de componentes", 3),
            ("Layout mecánico y eléctrico", 3),
            ("Revisión de seguridad y mantenibilidad", 1),
        ],
    ),
    (
        "2. Adquisición de datos por tipo de ensayo",
        [
            ("Corriente de fuga activa", 15),
            ("Corriente de fuga pasiva", 7),
            ("Resistencia de puesta a tierra", 15),
            ("Rigidez dieléctrica", 15),
        ],
    ),
    (
        "3. Arquitectura de comunicación",
        [
            ("Buses y protocolos (UART/I²C/SPI)", 8),
            ("Capas de comunicación y direccionamiento", 8),
            ("Pruebas de integridad, EMI y robustez", 5),
        ],
    ),
    (
        "4. Integración con módulos de medición",
        [("Integración eléctrica y lógica con sensores", 3), ("Verificación funcional básica", 2)],
    ),
    (
        "5. Conexionado interno",
        [
            ("Diseño (esquemáticos, calibres, protecciones)", 15),
            ("Implementación de mazos y cableado", 15),
        ],
    ),
    (
        "6. Módulos de control y procesamiento",
        [("Diseño lógico de control y procesamiento", 15), ("Implementación y validación", 15)],
    ),
]

SW = [
    (
        "1. Planificación y requerimientos",
        [
            ("Alcance del proyecto", 1),
            ("Normativas y estándares", 1),
            ("Dispositivos de prueba y protocolos", 2),
            ("Riesgos y seguridad", 1),
        ],
    ),
    (
        "2. Diseño del sistema y arquitectura",
        [
            ("Arquitectura del software", 7),
            ("Lenguajes, herramientas y tecnologías", 1),
            ("Diseño de la interfaz de usuario", 2),
            ("Estructura de la base de datos", 4),
        ],
    ),
    (
        "3. Procesamiento y almacenamiento",
        [
            ("Algoritmos de medición", 3),
            ("Integración con sensores y dispositivos", 2),
            ("Reportes y almacenamiento", 3),
        ],
    ),
    (
        "4. Interfaz de usuario",
        [
            ("Pantalla de configuración", 5),
            ("Monitoreo en tiempo real", 6),
            ("Alertas de seguridad y notificaciones", 5),
            ("Conexión con el procesamiento", 4),
        ],
    ),
    (
        "5. Pruebas y validación",
        [
            ("Pruebas unitarias", 7),
            ("Pruebas de integración", 4),
            ("Pruebas con dispositivos reales", 4),
        ],
    ),
    (
        "6. Documentación y entrenamiento",
        [
            ("Documentación del código", 3),
            ("Manual de usuario y operación", 3),
            ("Entrenamiento y revisión de seguridad", 2),
        ],
    ),
    ("7. Entrega final y soporte", [("Entrega de la interfaz", 2), ("Soporte y ajustes", 3)]),
]

PHASE_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3"]


def gantt(phases, fname, margin=0):
    """Gantt secuencial en días laborales, con sprints de 10 días."""
    rows = []
    t = 0
    for i, (phase, tasks) in enumerate(phases):
        start = t
        dur = sum(d for _, d in tasks)
        rows.append((phase, start, dur, i, True))
        for name, d in tasks:
            rows.append(("   " + name, t, d, i, False))
            t += d
    total = t
    end = total + margin

    fig, ax = plt.subplots(figsize=(13, 0.34 * len(rows) + 1.6))
    for y, (_name, s, d, i, is_phase) in enumerate(rows):
        col = PHASE_COLORS[i % len(PHASE_COLORS)]
        if is_phase:
            ax.barh(y, d, left=s, height=0.55, color=col, alpha=0.35, ec=col)
        else:
            ax.barh(y, d, left=s, height=0.5, color=col, ec="white")
            ax.text(s + d + 0.6, y, f"{d} d", va="center", fontsize=7.5, color="#333333")
    if margin:
        ax.barh(
            len(rows), margin, left=total, height=0.5, color="#BBBBBB", hatch="//", ec="#888888"
        )
        rows.append((f"Margen de tolerancia (hasta {margin} d)", 0, 0, 0, True))

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    for lab, r in zip(ax.get_yticklabels(), rows, strict=False):
        if r[4]:
            lab.set_fontweight("bold")
    ax.invert_yaxis()

    sprints = range(0, int(end) + 10, 10)
    ax.set_xticks(list(sprints))
    ax.set_xlim(0, (end // 10 + 1) * 10)
    ax.grid(axis="x", color="#CCCCCC", lw=0.8)
    ax.set_axisbelow(True)
    for k, x in enumerate(sprints):
        if x < end:
            ax.text(x + 5, -1.1, f"S{k + 1}", ha="center", fontsize=7.5, color="#555555")
    ax.set_xlabel("Días laborales (líneas verticales: sprints de 10 días)", fontsize=9)
    total_lbl = f"Total: {total} días" + (f" + {margin} de margen = {end} días" if margin else "")
    ax.set_title(total_lbl, fontsize=10, loc="right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=200, bbox_inches="tight")
    plt.close(fig)


arquitectura_dispositivo()
arquitectura_interfaz()
gantt(HW, "gantt_hardware.png", margin=10)
gantt(SW, "gantt_software.png")
print("ok")
