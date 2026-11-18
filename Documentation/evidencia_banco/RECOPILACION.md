# Recopilación de hallazgos, pruebas y evidencia — banco de ensayos (nov. 2026)

> **Documento de trabajo** (no es documentación formal): insumo para redactar el informe del
> proyecto en LaTeX. Período: 1 al 18 de noviembre de 2026. Autora: Valentina Ferrini.
> Repositorio: `C:\Users\valfe\OneDrive\SoftwareParaEnsayosDeSeguridadElectricaPortatil`
> (GitHub `vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil`, ramas `main` y `dev`).
> Rutas de este documento: relativas a la raíz del repositorio.

---

## 1. Resumen ejecutivo

- Se **alinearon los criterios de aprobación con IEC 60335-1** (ensayos de rutina del Anexo A,
  cap. 10 y 16.2): rigidez, fuga pasiva, puesta a tierra y consumo tenían límites incorrectos.
- Se armó un **banco de prueba real** (ESP32 + PZEM-004T + relé USB + contactor CHINT) y se
  validó de punta a punta **el ensayo de consumo** (final de línea y perfil), que es el único
  posible con el hardware actual.
- Se **escribió el firmware del ESP32** (no existía en el repositorio) y se integraron con la GUI
  todas las pestañas (Ensayos, Productos, Consumo, Configuraciones, Verificación, Exportar,
  Historial y Administración), que en el estado inicial eran mayormente un esqueleto sin lógica.
- Una **prueba de punta a punta en el banco** encontró 6 defectos (el más importante: el consumo
  se subestimaba ~27 % por promediar lecturas tomadas mientras el contactor cerraba); se
  corrigieron y se verificó la corrección en el banco.
- Se encontró y mitigó un **problema de compatibilidad electromagnética**: la placa de relés USB
  se reinicia al abrir el contactor con cargas con motor. El software quedó tolerante (falla
  segura, contactor abierto) y se agregó un varistor en la bobina; la causa no está eliminada.
- **Calidad de software**: tests automáticos de 63 → **158**; el CI de GitHub nunca había
  corrido los tests (mal configurado) y ahora pasa en verde (tests, lint y Docker).

---

## 2. Banco de pruebas armado

| Componente | Modelo / detalle | Evidencia |
|---|---|---|
| Microcontrolador | ESP32 NodeMCU-32S, USB-serie **CP2102** (COM4) | `fotos/01_esp32_pines_uart2_gpio16_17.jpg` |
| Medidor | **PZEM-004T v4.0 100 A** (con transformador de corriente toroidal) | `fotos/02_…`, `fotos/03_pzem004t_v4_placa_y_bornes.jpg` |
| Relés | Placa USB HID **dcttech USBRelay2** (2 canales, serie `BITFT`, VID 16C0 / PID 05DF) | — (detectada por software) |
| Contactor | **CHINT NXC-12M/22**, bobina 220 V~, 2 NA + 2 NC, AC-1 20 A / AC-3 12 A (3 kW) | `fotos/04_…frente.jpg`, `fotos/05_…etiqueta_bobina_220v.jpg` |
| Supresor | Varistor **ZOV 10D431K** (275 V AC) entre A1 y A2 | `fotos/08_varistor_zov_10d431k.jpg` |
| Protecciones | Fusibles 1 A (PZEM y bobina) y 10 A (DUT) en portafusible de panel; termomagnética Interelec C25 disponible (no apta como protección del banco: 25 A > 10 A del cableado) | `fotos/06_…`, `fotos/07_portafusible_panel.jpg` |
| Alimentación | Zapatilla con interruptor; **dos fichas macho con tierra** (una PZEM, otra contactor/DUT) en la misma zapatilla; **sin disyuntor diferencial** (decisión de la autora) | `../figuras/conexion_red_banco.svg` |
| Cargas de prueba | Soldador (~37 W, resistiva), ventilador (~52 W, motor), una carga no identificada (~6 W) | — |
| PC | Notebook Windows 11, Python 3.11 (uv), PyQt5 | — |

**Conexionado clave (validado):**
- ESP32 ↔ PZEM por **UART2**: GPIO16 (RX2) ← TX del PZEM, GPIO17 (TX2) → RX del PZEM,
  **VCC del PZEM al pin 3V3** del ESP32 (no a 5V, ver hallazgo H-13), GND común.
- Bornes del PZEM (numerados de izquierda a derecha con el conector de señal arriba): **1–2 =
  transformador de corriente** (10–80 Ω entre sí), **3 = N, 4 = L** (≈1 MΩ entre sí). Medido con
  multímetro por la autora; el circuito del TI está referido a la red (bornes 2–3 en pocos Ω).
- Relé 1: COM1 ← fase (tras fusible 1 A), NO1 → A1 de la bobina; A2 ← neutro.
- Contactor: 1→2 fase y 3→4 neutro al tomacorriente del DUT; R1–R4 (NC) sin usar; **tierra
  directa al DUT** sin pasar por el contactor; la fase de salida (borne 2) pasa por el TI.

**Diagramas:**
- `Documentation/figuras/mapa_cableado_esquema.jpg` — esquema original de la autora.
- `Documentation/figuras/mapa_cableado.svg` — versión ilustrada del esquema original.
- `Documentation/figuras/conexion_red_banco.svg` — conexión de red final del banco (dos fichas,
  fusibles, relé, contactor CHINT, TI, tierra directa).

---

## 3. Cronología

| Fecha | Hito |
|---|---|
| 01/11 | Revisión del proyecto; discrepancias de límites con la norma; corrección de rigidez, fuga pasiva, PAT y consumo (PR #1); CI apuntaba a `develop`; push y PR a `main`. |
| 01/11 | Diagnóstico de hardware: relé USB detectado; ESP32 no detectada (cable solo de carga). Backend `hidapi` para relés en Windows (PR #2). Mapa de cableado (PR #3). |
| 02/11 | ESP32 detectada con otro cable; faltaba driver CP2102; tenía **firmware AT de fábrica**. Se escribió y cargó el firmware propio (PR #4). |
| 10/11 | Conexión del PZEM: errores de cableado (TX0/RX0, luego bucle de arranque); solución con **PZEM a 3V3**. Primera lectura real: **229,7 V**. GUI instalable en Windows (PR #5). |
| 11/11 | Identificación de bornes del PZEM con multímetro; contactor CHINT; esquema de red y protecciones. |
| 12/11 | Banco completo: energización sin USB, relé → contactor OK. Primeras cargas: reinicios de la placa de relés (EMI). Software tolerante a la desconexión (PR #6); GUI principal integrada (PR #7). |
| 13/11 | Varistor 10D431K en la bobina. |
| 15/11 | Mediciones con ventilador (52 W) y soldador (37,6 W). |
| 17/11 | Todo a `main` (PR #9); CI arreglado (PR #10–11); correcciones de calibración (PR #12–13); **prueba de punta a punta** y corrección de 6 defectos (PR #14–15); pestañas Consumo y Exportar (PR #16–17). |
| 17–18/11 | API con clave nueva verificada; pestañas Configuraciones y Verificación (PR #18–19). |

---

## 4. Hallazgos

### 4.1 Normativos (criterios de aprobación)

Fuente: IEC 60335-1 ed. 4.1 (2004), `Documentation/IEC-60335-1.pdf` (no versionado, derechos de autor).
El equipo es de final de línea → **ensayos de rutina del Anexo A** donde existen.

| # | Ensayo | Estado inicial (código / docs) | Correcto según norma | PR |
|---|---|---|---|---|
| H-1 | Rigidez dieléctrica | Solo tensión: OK si > 800 V (Cl. I) / 2000 V (Cl. II); no medía corriente. Docs: "50 mA". | **A.2**: 1000 V (aislamiento básico, Cl. I) / 2500 V (doble/reforzado, Cl. II), 1 s; **FALLA si la corriente > 5 mA** (hasta 30 mA en aparatos con alta fuga). Los 50 mA son la capacidad del transformador, no un límite. | #1 |
| H-2 | Fuga pasiva | 1500 µA fijo | **16.2**: 0,75 mA (Clase I portátil); **duplicable** a 1,5 mA solo si el aparato cumple una condición (controles con posición de apagado en todos los polos, solo protector térmico, termostatos sin posición de apagado, o filtros de RF). | #1 |
| H-3 | Puesta a tierra | 100 mΩ fijo, sin controlar la corriente. Docs: "≤ 125 mΩ". | **A.1**: ≥ 10 A desde fuente ≤ 12 V; **200 mΩ** con cable fijo (medido desde la ficha) / **100 mΩ** sin cable fijo. | #1 |
| H-4 | Consumo | Porcentajes fijos: corriente 50–105 %, potencia 75–110 % | **Tablas 1 y 2 (cap. 10)**: tolerancia según tipo (calefacción/combinado o motor) y rango de potencia; se agregó un mínimo funcional no normativo del 50 %. | #1 |
| H-5 | Tabla de cotas del documento de formulación y `tablas_IEC60335.tex` | 125 mΩ, 50 mA, 750/1500 µA según ON/OFF, ±10 % | Valores de la norma (H-1 a H-4). `tablas_IEC60335.tex` reescrito. **Pendiente:** `Documentacion proyecto final.tex` y `seccion_hardware.tex` todavía dicen 125 mΩ / 50 mA. | #1 |

Tabla de tolerancias de consumo implementada (Tablas 1 y 2):

| Aparato | Potencia nominal (corriente) | Tolerancia |
|---|---|---|
| Todos | ≤ 25 W (≤ 0,2 A) | +20 % |
| Calefacción o combinado | > 25 W y ≤ 200 W (> 0,2 A y ≤ 1 A) | ±10 % |
| Calefacción o combinado | > 200 W (> 1 A) | +5 % o +20 W (+0,10 A), el mayor; −10 % |
| Motor | > 25 W y ≤ 300 W (> 0,2 A y ≤ 1,5 A) | +20 % |
| Motor | > 300 W (> 1,5 A) | +15 % o +60 W (+0,30 A), el mayor |

Otros límites de la norma no implementados: fuga Clase II 0,25 mA; aparatos fijos Clase I a motor 3,5 mA y de calefacción 0,75 mA/kW (máx. 5 mA).

### 4.2 Hardware y banco

| # | Hallazgo | Causa / diagnóstico | Resolución | Evidencia |
|---|---|---|---|---|
| H-10 | ESP32 no detectada por Windows | Cable USB solo de carga | Cambio de cable | Registro PnP de Windows |
| H-11 | ESP32 en "Otros dispositivos" | Faltaba driver Silicon Labs **CP210x** | Driver instalado (desde `silabser.inf` de la carpeta raíz, no desde `x64/`) | — |
| H-12 | La ESP32 no respondía a `PZEM1` | Tenía **firmware AT de fábrica** (`Bin version(Wroom32):1.1.2`, modo softAP) | Firmware propio (`firmware/esp32_pzem`, PlatformIO), cargado y verificado | PR #4 |
| H-13 | ESP32 en **bucle de arranque** (`invalid header: 0xffffffff`) con el PZEM conectado | (a) PZEM conectado a TX0/RX0 (los del USB) → no llegaban los comandos; (b) con el PZEM a 5 V su TX pone 5 V en GPIO16 y la ESP32 no arranca | PZEM a **GPIO16/17** y **VCC a 3V3** (el PZEM admite 3,3–5 V). Documentado en el firmware y en los diagramas. | `fotos/01_…`, `fotos/02_…`; PR #8 |
| H-14 | Bornes del PZEM sin serigrafía | — | Identificados por resistencia con multímetro (ver §2) | `fotos/03_…` |
| H-15 | **La placa de relés USB se desconecta** ("surprise removed" en Windows: 12/11 20:02:05 y 20:18:14, y en pruebas posteriores) | Interferencia al conmutar el contactor con carga, sobre todo **al abrir con una carga con motor** (ventilador). La placa dcttech usa un ATtiny con USB por software (V-USB), muy sensible. La ESP32 (CP2102) no se cayó nunca. | (1) Software tolerante: reintenta, **confirma relés apagados** o avisa "cortar la red" (PR #6); al reiniciarse, la placa deja los relés abiertos → **falla segura**. (2) Varistor 10D431K en A1–A2: mejoró pero no eliminó el problema. Con carga resistiva (soldador) no hubo reinicios. **Propuesta:** comandar el contactor desde un GPIO de la ESP32 con un módulo de relé optoacoplado. | Registro de eventos PnP; `fotos/08_…` |
| H-16 | Corriente 0 A con la pava | Pava sin funcionar / interruptor (no se repitió) | — | Salidas del notebook |
| H-17 | PZEM-004T 100 A no sirve para fuga | Arranca en ~20 mA; el límite de fuga es 0,75 mA | Requiere PZEM-004T 10 A (shunt) + red de medición IEC 60990 | — |

### 4.3 Software

| # | Hallazgo | Resolución | PR |
|---|---|---|---|
| H-20 | No había firmware del ESP32 en el repositorio | Firmware PlatformIO con protocolo `PZEM<n>`, `PING`, `INFO`, `SETADDR` | #4 |
| H-21 | Relés solo por `usbrelay_py` (Linux) | Backend `hidapi` (Windows y Linux), cantidad de relés leída de la placa; relé inexistente → error (no se ensaya con un circuito sin conmutar) | #2 |
| H-22 | Watchdog fijo en el relé 8 | `RELAY_WATCHDOG=0` desactiva (placa de 2 relés); `.env` local creado | #2 |
| H-23 | GUI no instalable en Windows (`PyQt5-Qt5` 5.15.18 sin wheel) | Fijado 5.15.2 solo en Windows | #5 |
| H-24 | La ventana principal era un esqueleto: botones sin lógica; `ProductForm`/`TestPanel` existían pero no se usaban | Integrados en Ensayos y Productos | #7 |
| H-25 | CI: "Run Tests" y "Lint" fallaban **desde el primer commit** (`uv sync` sin el extra `dev`: no había pytest ni ruff) | Workflow corregido; 62 errores de ruff corregidos | #10 |
| H-26 | Correcciones de calibración `CORRECTION_*` **nunca se aplicaban** | Aplicadas a todas las lecturas | #12 |
| H-27 | **Consumo subestimado ~27 %** (soldador 27 W → FALLA): el promedio incluía lecturas tomadas mientras cerraba el contactor (0 W, 26 W, luego 37 W) | Se descartan las primeras `TEST_CONSUMPTION_SETTLE` = 2 lecturas; en el banco: **36,8 W, OK** | #14 |
| H-28 | La UI quedaba colgada "ensayando" ante una excepción (ej. relé inexistente), sin mostrar error | La UI se libera al terminar el hilo; relés apagados; aviso con el error | #14 |
| H-29 | Modo cíclico: UI liberada tras el 1.er ciclo; se podía lanzar otro ensayo encima | UI bloqueada hasta el último ciclo; PARADA entre ciclos no se pierde | #14 |
| H-30 | Historial: columnas "A Medida" y "W Medida" vacías (clave `A_medida` vs `a_medida`); decimales de más | Corregido; resolución del PZEM | #14 |
| H-31 | Fuga sin medidor → NO_EJECUTADO (y rigidez sin lecturas) | En ensayos de seguridad, lectura fallida del medidor → **FALLA** | #14 |
| H-32 | API con **admin/admin en texto plano** | Hash PBKDF2-SHA256; la API rechaza (503) las credenciales de fábrica; `scripts/cambiar_clave_admin.py` | #14 |
| H-33 | Cerrar la ventana no detenía el ensayo (hilo seguía ~4 s) | Se detiene antes de apagar el hardware (0,4 s) | #14 |
| H-34 | Perfil de consumo: 1.ª muestra 23 W (PZEM sin actualizar a los 2 s) | Estabilización propia del perfil: 3 s | #16 |
| H-35 | Los gráficos del `.ui` eran `LivePlotWidget` de pglive; el diccionario pasado a `loadUi` no tenía efecto | Dibujo sobre esos gráficos (`PlotSeries`) | #16 |
| H-36 | Exportación a USB solo funcionaba en Linux (`/media`) | Selector de carpeta | #16 |
| H-37 | Duraciones de ensayo solo desde `.env`; tabla `tiempos` sin uso | Los ensayos usan la tabla (editable en Configuraciones) | #18 |
| H-38 | Panel de Administración inaccesible; ruta de `.ui` dependía de la carpeta de ejecución | Menú Archivo → Administración…; ruta relativa al paquete | #18 |
| H-39 | `data/ensayos.db` versionado en git: cambia con cada uso (y contiene el hash de la clave) | **Pendiente**: sacarlo del repositorio | — |

---

## 5. Pruebas realizadas y resultados

### 5.1 Comunicación y medición básica

| Prueba | Resultado |
|---|---|
| ESP32 + firmware: `PING`, `INFO` | `PONG`, `INFO:FW=1.0.0,PZEM=3` |
| PZEM1 sin red | `PZEM1:ERROR` (esperado) |
| PZEM1 con red (sin carga) | **229,7 V / 0 A** (10/11); 230,0 V (12/11); 231,4 V y 226,6 V (17/11) |
| PZEM2 / PZEM3 (no instalados) | `ERROR` (esperado) |
| Relé USB: estado y conmutación | 2 relés, confirmación de estado ON/OFF por la placa |
| Energización sin USB (12/11) | Solo LED D4 del PZEM; contactor en reposo; DUT sin tensión |
| Relé 1 → contactor (2 s) | El contactor cerró y abrió ("clac") |

### 5.2 Mediciones con carga (TI en la fase del DUT)

| Carga | Fecha | V | A | W | FP | Observación |
|---|---|---|---|---|---|---|
| Carga no identificada | 12/11 | 229,3 | 0,068 | 6,3 | 0,40 | La placa de relés se desconectó durante la medición (H-15) |
| Ventilador | 15/11 | 228,7–228,9 | 0,236–0,242 | 52,1–53,4 | 0,96–0,97 | Reinicio de la placa al abrir; recuperada al 3.er intento (PR #6) |
| Soldador | 15/11 | 230,1–230,2 | 0,163–0,164 | 37,5–37,7 | 1,00 | Sin reinicios (carga resistiva) |
| Soldador (prueba E2E, antes del fix) | 17/11 | ~228 | ~0,14 | **27,2** (prom.) | ~0,79 | FALLA por promedio con lecturas transitorias (H-27) |
| Soldador (después del fix) | 17/11 | 227,7–228,0 | 0,161–0,162 | **36,6–36,8** | 0,99–1,00 | **OK** (calefacción 40 W, ±10 %: 36–44 W) |

Fuente: `datos/notebook_comandos_con_salidas.ipynb` (salidas del 15/11) y
`datos/banco_pruebas_2026-11-17.db` (tabla `historial_fdl`).

### 5.3 Prueba de punta a punta (17/11) — antes de corregir

Ventana principal real, hardware real, soldador. Base de datos aparte.

| Área | Resultado |
|---|---|
| Hardware detectado por la GUI | ✅ ESP32 (COM4), relé BITFT |
| Productos: alta, validación, edición, baja, búsqueda, persistencia | ✅ (12/12 verificaciones) |
| Botones de Consumo, Verificación, Configuraciones, Exportar | ❌ sin lógica (7 botones) → conectados luego (PR #16, #18) |
| Consumo final de línea | ✅ corre / ❌ subestimado (H-27) |
| Cíclico 3 ciclos | ✅ ejecuta / ❌ UI liberada antes (H-29) |
| PARADA | ✅ corta en 0,6 s, relés apagados |
| Fuga activa / pasiva sin PZEM2 | ⚠️ NO_EJECUTADO (H-31) |
| PAT / rigidez (relés 3–7 inexistentes) | ❌ UI colgada (H-28); relés apagados |
| Cerrar en medio de un ensayo | ✅ relés apagados / ⚠️ hilo seguía 4 s (H-33) |
| Historial | ✅ guardado / ❌ columnas vacías (H-30) |
| Exportación Excel (función) | ✅ 3 hojas |
| API REST | ✅ health 200; 401 sin clave o clave incorrecta; 200 con credenciales; `/app/` 200 / ⚠️ admin/admin (H-32) |
| Mail | ➖ no probado (sin SMTP) |

### 5.4 Verificación de las correcciones en el banco (17/11, PR #14)

| Corrección | Resultado en el banco |
|---|---|
| Estabilización del consumo | 36,8 W, OK |
| Cíclico | UI liberada al final del 3.er ciclo (22,1 s); 3 registros |
| Error de ensayo | Aviso visible; UI libre en 0,5 s; relés en 0 |
| Fuga sin PZEM2 | FALLA |
| Historial | Columnas con datos, resolución del PZEM |
| Cerrar en medio de un ensayo | Detiene el hilo en 0,4 s; relés en 0 |

### 5.5 Perfil de consumo y exportación (17/11, PR #16)

| Prueba | Resultado |
|---|---|
| Perfil 20 s, muestra cada 5 s (soldador) | 5 muestras; 1.ª 23,1 W (H-34) y luego 36,1–36,2 W, FP 1,00; contactor cerrado solo durante el perfil |
| Perfil tras el ajuste (3 s de estabilización) | 3 muestras de 36,2–36,4 W desde la primera |
| PARADA a los 8 s | Cortó con 2 muestras; contactor abierto |
| Gráficos, valores en vivo, cuentas regresivas | Actualizados en cada muestra |
| Buscar por serie | Filtra el historial |
| Exportar a carpeta | `exportacion_historial_2026-11-17.xlsx` (FDL 16 filas, CONSUMO 7, VERIFICACIÓN 0) |
| Mail sin SMTP | Aviso correcto |

Datos: `datos/banco_pruebas_2026-11-17.db` (tabla `ensayos_consumo`, 10 muestras) y
`datos/exportacion_historial_2026-11-17.xlsx`.

### 5.6 API con la clave nueva (18/11)

Clave cambiada con `scripts/cambiar_clave_admin.py` (guardada con hash). `admin/admin` → 401;
sin credenciales → 401; con la clave nueva (probado por la autora en el navegador) → historial OK.

### 5.7 Pruebas no realizadas en el banco

- Configuraciones y Verificación (PR #18): probadas solo con la ventana real y hardware simulado,
  por decisión de la autora.
- Fuga activa/pasiva, PAT, rigidez y verificación con patrones: **falta hardware** (§7).

### 5.8 Pruebas automáticas e integración continua

| Momento | Tests (pytest) | CI GitHub |
|---|---|---|
| Inicio (01/11) | 63 tras las correcciones normativas | "Run Tests" y "Lint" fallaban siempre |
| PR #14 | 114 | Verde (tras PR #10) |
| PR #16 | 132 | Verde |
| PR #18 (final) | **158** | **Verde**: Run Tests, Lint Code, Run Tests in Docker |

Los tests cubren: veredictos por la norma, tolerancias de consumo, ensayos con hardware simulado,
relés (incluida la reconexión), watchdog, correcciones de calibración, credenciales, perfil de
consumo (reloj simulado), ventana principal y todas las pestañas (Qt offscreen).

---

## 6. Estado por funcionalidad (18/11)

| Funcionalidad | Estado |
|---|---|
| Ensayo de consumo (final de línea) | ✅ validado en el banco |
| Perfil de consumo (gráficos, muestras) | ✅ validado en el banco |
| Modo cíclico y PARADA | ✅ validado en el banco |
| Productos (ABM) y base de datos | ✅ validado |
| Historial y exportación (escritorio, carpeta) | ✅ validado |
| Exportación por mail | ⚠️ implementado, sin SMTP para probar |
| Configuraciones (tiempos) | ✅ implementado y probado sin banco |
| Verificación con patrones | ⚠️ implementado; requiere hardware de fuga/PAT/rigidez |
| API REST + autenticación | ✅ validado |
| Fuga activa / pasiva | ❌ falta PZEM2 + red de medición |
| Puesta a tierra | ❌ falta PZEM3 + transformador 2,2 V/15 A conectado + relés |
| Rigidez dieléctrica | ❌ falta transformador de AT, medición de corriente en AT y relés |

---

## 7. Pendientes y limitaciones

1. **Hardware para los ensayos de seguridad**: PZEM-004T 10 A + red IEC 60990 (fuga), PZEM3 +
   transformador 2,2 V/15 A (verificar que entregue ≥ 10 A) para PAT, transformador de AT
   1000/2500 V con medición de 5 mA y protecciones para rigidez; más relés (o reasignación de
   los 2 relés por `.env` en cada sesión).
2. **EMI de la placa de relés** con cargas con motor: pasar el control del contactor a la ESP32
   (relé optoacoplado en GPIO; el firmware ya acepta `RELAYON/RELAYOFF`); ferritas y separación
   de cables USB/220 V; aislador USB (ADuM3160) recomendado.
3. **Calibración** contra un instrumento patrón (`CORRECTION_*`, `DIELECTRIC_CURRENT_MULTIPLIER`,
   factores de escala); la potencia no tiene corrección propia.
4. Sin **disyuntor diferencial** en el banco (decisión de la autora): mitigado con
   procedimiento (no tocar nada energizado, desconectar antes de manipular).
5. SMTP sin configurar (mail no probado).
6. `data/ensayos.db` versionado en git (contiene el hash de la clave): sacarlo del repositorio.
7. Documentación con valores viejos: `Documentacion proyecto final.tex` y `seccion_hardware.tex`
   (125 mΩ / 50 mA); hardware docs dicen 30 mA vs 50 mA del transformador de AT.
8. Empaquetado (`pyproject` empaqueta `src`): los comandos `ensayos-gui`/`ensayos-api` no
   funcionan instalados; se lanza con `python -m` y `PYTHONPATH=src`.
9. Guardar la tensión y corriente medidas de rigidez en el historial (hoy solo el veredicto).

---

## 8. Índice de evidencia

### 8.1 Fotos (`Documentation/evidencia_banco/fotos/`)

| Archivo | Contenido |
|---|---|
| `01_esp32_pines_uart2_gpio16_17.jpg` | NodeMCU-32S con los cables de datos en P16 (naranja → TX del PZEM) y P17 (amarillo → RX) |
| `02_pzem_conector_senal_gnd_tx_rx_vcc.jpg` | Conector de señal del PZEM (GND, TX, RX, VCC; serigrafía VCC = 3,3–5,0 V) |
| `03_pzem004t_v4_placa_y_bornes.jpg` | PZEM-004T-100A v4.0 completo; bornera de potencia sin serigrafía |
| `04_contactor_chint_nxc12m22_frente.jpg` | Contactor CHINT NXC-12M/22: bornes R1, 1, 3, R3, A1 / R2, 2, 4, R4, A2 |
| `05_contactor_chint_etiqueta_bobina_220v.jpg` | Etiqueta: IEC/EN 60947-4-1, Ie(AC-1)=Ith=20 A, AC-3 12 A / 3 kW a 220–230 V, bobina 220 V |
| `06_termomagnetica_interelec_c25.jpg` | Termomagnética Interelec INT-U25, C25, 3000 A (no usada como protección del banco) |
| `07_portafusible_panel.jpg` | Portafusible de panel 5×20 mm (fusibles de 1 A) |
| `08_varistor_zov_10d431k.jpg` | Varistor ZOV 10D431K (275 V AC) colocado en A1–A2 |

### 8.2 Diagramas (`Documentation/figuras/`)

- `mapa_cableado_esquema.jpg` (original de la autora), `mapa_cableado.svg` (ilustrado),
  `conexion_red_banco.svg` (red, protecciones y control del banco final).

### 8.3 Datos (`Documentation/evidencia_banco/datos/`)

| Archivo | Contenido |
|---|---|
| `banco_pruebas_2026-11-17.db` | Base SQLite de la prueba de punta a punta: `historial_fdl` (16 ensayos del 17/11, antes y después de las correcciones) y `ensayos_consumo` (10 muestras de perfil) |
| `exportacion_historial_2026-11-17.xlsx` | Excel exportado por la aplicación desde el banco (hojas FDL, CONSUMO, VERIFICACIÓN) |
| `notebook_comandos_con_salidas.ipynb` | Notebook de comandos con las salidas reales del 15/11 (ventilador y soldador) |

### 8.4 Scripts de prueba (`Documentation/evidencia_banco/scripts_prueba/`)

Scripts usados para las pruebas en el banco (manejan la ventana real con el hardware real):
`e2e_gui_db.py` (GUI y base), `e2e_ensayos.py` y `e2e_ensayos2.py` (ensayos, cíclico, PARADA,
cierre), `e2e_correcciones.py` (verificación de las correcciones), `e2e_export_api.py`
(Excel y API), `e2e_consumo_exportar.py` (perfil de consumo y exportación).
Herramientas permanentes del repositorio: `scripts/diagnostico_esp32.py`,
`scripts/diagnostico_rele.py`, `scripts/cambiar_clave_admin.py`, `Documentation/useful_commands.ipynb`.

### 8.5 Pull requests (GitHub `vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil`)

| PR | Tema |
|---|---|
| [#1](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/1) | Límites de IEC 60335-1 y documentación LaTeX |
| [#2](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/2) | Backend hidapi para relés, diagnóstico, watchdog desactivable |
| [#3](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/3) | Mapa de cableado |
| [#4](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/4) | Firmware del ESP32 |
| [#5](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/5) | GUI instalable en Windows |
| [#6](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/6) | Tolerancia a la desconexión de la placa de relés |
| [#7](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/7) | Paneles de Ensayos y Productos en la ventana principal |
| [#8](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/8) | Diagrama de red y PZEM a 3V3 |
| [#9](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/9) | Integración a main |
| [#10](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/10) / [#11](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/11) | CI que corre tests y lint |
| [#12](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/12) / [#13](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/13) | Correcciones de calibración aplicadas |
| [#14](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/14) / [#15](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/15) | Correcciones de la prueba de punta a punta |
| [#16](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/16) / [#17](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/17) | Pestañas Consumo y Exportar |
| [#18](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/18) / [#19](https://github.com/vivadig/SoftwareParaEnsayosDeSeguridadElectricaPortatil/pull/19) | Pestañas Configuraciones y Verificación; Administración |

Cada PR tiene en su descripción el detalle de cambios, pruebas y puntos a revisar.

---

## 9. Sugerencias para el informe

- **Metodología**: ensayos de rutina (Anexo A) vs. de tipo; criterio "peor caso del intervalo"
  (rigidez, PAT) vs. "promedio" (consumo); estabilización tras cerrar el contactor (2 s final de
  línea, 3 s perfil); lectura fallida del medidor = FALLA en ensayos de seguridad.
- **Resultados**: tabla §5.2 (consumo con carga resistiva: error del valor medido vs. nominal del
  soldador; sin instrumento patrón todavía, no es una validación metrológica).
- **Problemas encontrados**: EMI (H-15) como lección de diseño (supresor en bobinas, aislación
  galvánica del USB, preferir microcontrolador con USB por hardware).
- **Seguridad**: falla segura de los relés, bloqueo de hardware compartido, protecciones del
  banco (fusibles, tierra directa al DUT) y ausencia de diferencial.
- **Calidad**: evolución de tests 63 → 158 y CI en verde.
- **Trabajo futuro**: §7.
