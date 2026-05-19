# Software para Ensayos de Seguridad Eléctrica Portátil

Software para gestión y control de ensayos de seguridad eléctrica portátil usando el módulo de relés USB HW-554.

## Hardware Soportado

**Módulo de Relés**: HW-554 / 200765
- 8 canales de relés controlados por USB
- Alimentación: DC 12V, >300mA
- Capacidad: AC 250V 10A / DC 30V 10A
- Conexión USB HID (plug and play, sin drivers)
- Documentación: `docs/HW-554-200765.pdf`

## Características

- ✅ Control de relés USB mediante librería `usbrelay`
- ✅ Actualización automática de `usbrelay` en cada build de Docker
- ✅ Interfaz Python con `RelayController` para control simplificado
- ✅ Tests unitarios completos con mocks
- ✅ Entorno de desarrollo con Docker o local (uv)
- ✅ CI/CD con GitHub Actions
- ✅ Pre-commit hooks (ruff, tests)

## Requisitos Previos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Gestor de paquetes Python ultrarrápido
- Docker y Docker Compose (opcional, para ejecutar tests en contenedores)

## Instalación de uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Configuración del Proyecto

### Opción A: Desarrollo en Docker (Sin instalación local)

Si prefieres trabajar completamente en Docker:

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd SoftwareParaEnsayosDeSeguridadElectricaPortatil

# 2. Levantar el contenedor
docker compose -f docker/docker-compose.yaml up -d

# 3. Acceder al contenedor
docker compose -f docker/docker-compose.yaml exec app bash

# Ahora puedes ejecutar comandos dentro del contenedor:
# uv run pytest
# uv run ruff check .
```

### Opción B: Desarrollo Local

Si prefieres trabajar con Python instalado localmente:

#### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd SoftwareParaEnsayosDeSeguridadElectricaPortatil
```

#### 2. Crear entorno virtual e instalar dependencias

```bash
# uv creará automáticamente el entorno virtual e instalará las dependencias
uv sync
```

#### 3. Configurar pre-commit hooks

```bash
# Instalar los hooks de pre-commit
uv run pre-commit install

# (Opcional) Ejecutar pre-commit en todos los archivos
uv run pre-commit run --all-files
```

## Estructura del Proyecto

```
.
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI pipeline
├── docker/
│   ├── Dockerfile              # Imagen Docker para la aplicación
│   ├── docker-compose.yaml     # Compose para desarrollo
│   ├── docker-compose-testing.yaml  # Compose para ejecutar tests
│   └── entrypoint.sh           # Script de entrada del contenedor
├── src/                        # Código fuente de la aplicación
├── tests/                      # Tests del proyecto
├── .pre-commit-config.yaml     # Configuración de pre-commit
├── .python-version             # Versión de Python del proyecto
├── pyproject.toml              # Configuración del proyecto y dependencias
├── pytest.ini                  # Configuración de pytest
└── README.md                   # Este archivo
```

## Desarrollo

### Uso del Controlador de Relés

El proyecto incluye un controlador Python para el módulo HW-554:

```python
from src.relay_controller import RelayController

# Inicializar el controlador
controller = RelayController()

# Ver placas conectadas
print(f"Placas conectadas: {controller.board_count}")
for board in controller.get_boards():
    print(f"Serial: {board['serial']}, Path: {board['path']}")

# Obtener IDs de todos los relés
relay_ids = controller.get_relay_ids()  # ["QGAKC_1", "QGAKC_2", ..., "QGAKC_8"]

# Controlar relés individuales
controller.turn_on(relay_ids[0])   # Enciende relé 1
controller.turn_off(relay_ids[0])  # Apaga relé 1

# Control directo
controller.control_relay("QGAKC_1", True)   # Enciende
controller.control_relay("QGAKC_1", False)  # Apaga
```

**Nota**: El módulo `usbrelay` solo está disponible dentro del contenedor Docker. Para desarrollo local, los tests usan mocks.

### Ejecutar código con el hardware

```bash
# En Docker (con hardware conectado)
docker compose -f docker/docker-compose.yaml up -d
docker compose -f docker/docker-compose.yaml exec app python3.11 src/relay_controller.py
```

### Ejecutar tests

```bash
# Ejecutar todos los tests
uv run pytest

# Ejecutar tests con cobertura
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Ejecutar tests específicos
uv run pytest tests/test_example.py

# Ejecutar tests en modo verbose
uv run pytest -v
```

### Linting y Formateo

```bash
# Ejecutar linter (ruff)
uv run ruff check .

# Ejecutar linter con auto-fix
uv run ruff check . --fix

# Ejecutar formateador
uv run ruff format .

# Verificar formato sin modificar
uv run ruff format --check .
```

### Pre-commit

Los pre-commit hooks se ejecutan automáticamente antes de cada commit y realizan:

1. **Ruff lint** - Verifica y corrige problemas de código
2. **Ruff format** - Formatea el código automáticamente
3. **UV lock** - Asegura que `uv.lock` esté actualizado
4. **UV export** - Exporta `requirements.txt` desde `uv.lock`
5. **Tests** - Ejecuta los tests para asegurar que todo funciona

```bash
# Ejecutar pre-commit manualmente
uv run pre-commit run --all-files

# Saltar pre-commit hooks (no recomendado)
git commit --no-verify
```

## Docker

### Desarrollo en Docker (sin instalación local)

Si prefieres trabajar completamente en Docker sin instalar nada localmente:

```bash
# Levantar el contenedor en modo desarrollo
docker compose -f docker/docker-compose.yaml up -d

# Ver logs
docker compose -f docker/docker-compose.yaml logs -f

# Ejecutar comandos dentro del contenedor
docker compose -f docker/docker-compose.yaml exec app uv run pytest
docker compose -f docker/docker-compose.yaml exec app uv run ruff check .

# Acceder a la shell del contenedor
docker compose -f docker/docker-compose.yaml exec app bash

# Detener el contenedor
docker compose -f docker/docker-compose.yaml down
```

El contenedor monta los directorios `src/`, `tests/` y archivos de configuración como volúmenes, por lo que puedes editar el código en tu editor local y los cambios se reflejan inmediatamente en el contenedor.

### Ejecutar tests en Docker

```bash
# Construir y ejecutar tests en Docker
docker compose -f docker/docker-compose-testing.yaml up --build

# Ejecutar tests y eliminar contenedores
docker compose -f docker/docker-compose-testing.yaml up --build --abort-on-container-exit

# Ver logs
docker compose -f docker/docker-compose-testing.yaml logs -f
```

### Comandos disponibles en el contenedor

El contenedor Docker incluye los siguientes comandos:

```bash
# Ejecutar tests
docker compose -f docker/docker-compose-testing.yaml run app test

# Ejecutar tests con cobertura
docker compose -f docker/docker-compose-testing.yaml run app coverage

# Ejecutar linter
docker compose -f docker/docker-compose-testing.yaml run app lint

# Ejecutar formateador
docker compose -f docker/docker-compose-testing.yaml run app format

# Abrir shell interactivo
docker compose -f docker/docker-compose-testing.yaml run app shell
```

## CI/CD

El proyecto incluye un pipeline de CI/CD con GitHub Actions que se ejecuta en:

- **Push** a las ramas `main` y `develop`
- **Pull Requests** a `main` y `develop`
- **Tags** que comienzan con `v*`

### Jobs del Pipeline

1. **Lint**: Verifica el código con Ruff (formato y linting)
2. **Test**: Ejecuta los tests con pytest
3. **Test Docker**: Ejecuta los tests dentro de un contenedor Docker
4. **Coverage**: Genera reportes de cobertura de código (solo en `main`)

## Agregar Dependencias

```bash
# Agregar dependencia de producción
uv add <paquete>

# Agregar dependencia de desarrollo
uv add --dev <paquete>

# Actualizar todas las dependencias
uv lock --upgrade

# Sincronizar entorno con uv.lock
uv sync
```

## Buenas Prácticas

1. **Siempre ejecutar tests antes de hacer commit**
   - Los pre-commit hooks lo harán automáticamente

2. **Mantener cobertura de tests alta**
   - Apuntar a >80% de cobertura de código

3. **Seguir las convenciones de código**
   - Ruff se encargará de esto automáticamente

4. **Escribir mensajes de commit descriptivos**
   - Usar formato convencional: `tipo: descripción`
   - Ejemplos: `feat: agregar función X`, `fix: corregir bug Y`

5. **Mantener el código documentado**
   - Agregar docstrings a funciones y clases
   - Mantener este README actualizado

## Solución de Problemas

### Pre-commit hooks fallan

```bash
# Actualizar pre-commit
uv run pre-commit autoupdate

# Re-instalar hooks
uv run pre-commit uninstall
uv run pre-commit install
```

### Tests fallan en Docker

```bash
# Limpiar contenedores y volúmenes
docker compose -f docker/docker-compose-testing.yaml down -v

# Re-construir imagen desde cero
docker compose -f docker/docker-compose-testing.yaml build --no-cache
```

### Problemas con uv

```bash
# Limpiar cache de uv
uv cache clean

# Re-sincronizar entorno
rm -rf .venv
uv sync
```

## Contribuir

1. Crear una rama desde `develop`
2. Realizar cambios
3. Ejecutar tests y linting localmente
4. Hacer commit (los pre-commit hooks se ejecutarán)
5. Crear Pull Request hacia `develop`
6. Esperar aprobación del CI/CD

## Licencia

[Especificar licencia]
