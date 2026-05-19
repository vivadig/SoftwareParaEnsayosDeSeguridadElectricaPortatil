"""Controlador para relés USB HW-554 usando usbrelay."""

import usbrelay_py


class RelayController:
    """Controlador para módulo de relés USB HW-554."""

    RELAY_COUNT = 8

    def __init__(self):
        """Inicializa el controlador de relés.

        board_count() debe llamarse primero para enumerar los dispositivos.
        """
        self.board_count = usbrelay_py.board_count()

    def get_boards(self):
        """
        Obtiene información de todas las placas conectadas.

        Returns:
            list[tuple]: Lista de tuplas (serial, relay_count, state).
                         state es un bitmask del estado de los relés.
        """
        return usbrelay_py.board_details()

    def control_relay(self, serial: str, relay_number: int, state: int):
        """
        Controla un relé específico.

        Args:
            serial: Serial de la placa (ejemplo: "6QMBS").
            relay_number: Número del relé (1-8).
            state: 1 para encender, 0 para apagar.

        Returns:
            int: Resultado del comando.
        """
        return usbrelay_py.board_control(serial, relay_number, state)

    def turn_on(self, serial: str, relay_number: int):
        """
        Enciende un relé.

        Args:
            serial: Serial de la placa.
            relay_number: Número del relé (1-8).
        """
        return self.control_relay(serial, relay_number, 1)

    def turn_off(self, serial: str, relay_number: int):
        """
        Apaga un relé.

        Args:
            serial: Serial de la placa.
            relay_number: Número del relé (1-8).
        """
        return self.control_relay(serial, relay_number, 0)

    def get_first_serial(self):
        """
        Obtiene el serial de la primera placa conectada.

        Returns:
            str | None: Serial de la primera placa, o None si no hay placas.
        """
        boards = self.get_boards()
        if not boards:
            return None
        return boards[0][0]


# Ejemplo de uso
if __name__ == "__main__":
    controller = RelayController()

    print(f"Placas conectadas: {controller.board_count}")
    print("\nDetalles de placas:")
    for board in controller.get_boards():
        serial, relay_count, state = board
        print(f"  - Serial: {serial}, Relés: {relay_count}, Estado: {state:#010b}")

    serial = controller.get_first_serial()
    if serial:
        # Encender relé 1
        controller.turn_on(serial, 1)
        print("\nRelé 1 encendido")

        # Ver estado
        for board in controller.get_boards():
            s, rc, state = board
            print(f"  Estado: {state:#010b}")

        # Apagar relé 1
        controller.turn_off(serial, 1)
        print("Relé 1 apagado")
