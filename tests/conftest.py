"""Configuración compartida de pytest."""

import sys
from unittest.mock import MagicMock

# usbrelay_py solo está disponible dentro del contenedor Docker; se simula para
# poder importar el paquete de hardware en desarrollo local.
sys.modules.setdefault("usbrelay_py", MagicMock())
