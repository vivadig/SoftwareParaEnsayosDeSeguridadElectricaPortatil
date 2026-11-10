/**
 * Firmware del ESP32 del banco de ensayos de seguridad eléctrica.
 *
 * Atiende comandos de texto por el puerto USB (115200 baudios, una línea por
 * comando terminada en '\n') y responde una línea por comando. Es el protocolo
 * que usa ensayos.hardware.esp32_client.ESP32Client.
 *
 * Comandos:
 *   PING          -> PONG
 *   INFO          -> INFO:FW=<versión>,PZEM=<cantidad>
 *   PZEM<n>       -> PZEM<n>:V=<V>,C=<A>,P=<W>,E=<kWh>,FP=<fp>
 *                    PZEM<n>:ERROR  (el módulo no respondió o n no existe)
 *   SETADDR<a>    -> SETADDR:OK / SETADDR:ERROR
 *                    Graba la dirección Modbus <a> (1-247) en el PZEM conectado.
 *                    Usar con UN SOLO PZEM en el bus.
 *   RELAYON<n>    -> RELE<n>_ON  / RELE<n>_ERROR
 *   RELAYOFF<n>   -> RELE<n>_OFF / RELE<n>_ERROR
 *   (otro)        -> ERROR:COMANDO_DESCONOCIDO
 *
 * Conexión de los PZEM (todos en el mismo bus UART2, cada uno con su dirección):
 *   ESP32 GPIO17 (TX2) -> RX del PZEM
 *   ESP32 GPIO16 (RX2) <- TX del PZEM
 *   ESP32 3V3 / GND    -> VCC / GND del PZEM
 *   El PZEM debe alimentarse con 3,3 V: con 5 V, su salida TX pone 5 V en GPIO16
 *   y el ESP32 no arranca ("invalid header: 0xffffffff" en bucle).
 *
 * PZEM1 = consumo, PZEM2 = fuga / rigidez dieléctrica, PZEM3 = puesta a tierra.
 * Con varios PZEM en el bus, cada uno debe tener grabada su dirección (1, 2, 3)
 * con SETADDR antes de conectarlos juntos. Con un solo PZEM conectado, PZEM1
 * usa la dirección general y responde sin configuración previa.
 */

#include <Arduino.h>
#include <PZEM004Tv30.h>

namespace {

constexpr const char* kFirmwareVersion = "1.0.0";
constexpr uint32_t kHostBaud = 115200;
constexpr int kPzemRxPin = 16;
constexpr int kPzemTxPin = 17;
constexpr size_t kMaxLineLength = 64;

// Dirección Modbus de cada PZEM. PZEM1 usa la general (0xF8) mientras haya uno
// solo; al sumar más módulos, grabarle la 1 y cambiar este valor a 0x01.
constexpr uint8_t kPzemAddresses[] = {PZEM_DEFAULT_ADDR, 0x02, 0x03};
constexpr size_t kPzemCount = sizeof(kPzemAddresses) / sizeof(kPzemAddresses[0]);

// Pines de relés manejados por el ESP32 (el banco usa relés USB, así que no
// hay ninguno). Para agregar uno: listar su GPIO, p. ej. {26, 27}.
constexpr int kRelayPins[] = {-1};
constexpr bool kRelayActiveLow = true;

PZEM004Tv30* pzems[kPzemCount];
String inputLine;

/** Responde una línea al host. */
void reply(const String& line) { Serial.println(line); }

/** Lee el número que sigue a un prefijo; devuelve -1 si no hay un entero válido. */
long parseSuffix(const String& command, const char* prefix) {
  String digits = command.substring(strlen(prefix));
  if (digits.length() == 0) {
    return -1;
  }
  for (size_t i = 0; i < digits.length(); ++i) {
    if (!isDigit(digits[i])) {
      return -1;
    }
  }
  return digits.toInt();
}

void handlePzem(long index) {
  String prefix = "PZEM" + String(index) + ":";
  if (index < 1 || index > static_cast<long>(kPzemCount)) {
    reply(prefix + "ERROR");
    return;
  }
  PZEM004Tv30* pzem = pzems[index - 1];
  float voltage = pzem->voltage();
  if (isnan(voltage)) {
    // Sin respuesta: módulo desconectado, sin tensión de red o dirección errónea
    reply(prefix + "ERROR");
    return;
  }
  float current = pzem->current();
  float power = pzem->power();
  float energy = pzem->energy();
  float pf = pzem->pf();
  if (isnan(current) || isnan(power) || isnan(energy) || isnan(pf)) {
    reply(prefix + "ERROR");
    return;
  }
  reply(prefix + "V=" + String(voltage, 2) + ",C=" + String(current, 3) +
        ",P=" + String(power, 2) + ",E=" + String(energy, 3) + ",FP=" + String(pf, 2));
}

void handleSetAddress(long address) {
  if (address < 1 || address > 247) {
    reply("SETADDR:ERROR");
    return;
  }
  // La dirección general (0xF8) llega a cualquier PZEM, por eso solo debe haber uno
  PZEM004Tv30 general(Serial2, kPzemRxPin, kPzemTxPin, PZEM_DEFAULT_ADDR);
  reply(general.setAddress(static_cast<uint8_t>(address)) ? "SETADDR:OK" : "SETADDR:ERROR");
}

void handleRelay(long index, bool on) {
  String prefix = "RELE" + String(index);
  constexpr size_t relayCount = sizeof(kRelayPins) / sizeof(kRelayPins[0]);
  if (index < 1 || index > static_cast<long>(relayCount) || kRelayPins[index - 1] < 0) {
    reply(prefix + "_ERROR");
    return;
  }
  digitalWrite(kRelayPins[index - 1], (on != kRelayActiveLow) ? HIGH : LOW);
  reply(prefix + (on ? "_ON" : "_OFF"));
}

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();
  if (command.length() == 0) {
    return;
  }
  if (command == "PING") {
    reply("PONG");
  } else if (command == "INFO") {
    reply("INFO:FW=" + String(kFirmwareVersion) + ",PZEM=" + String(kPzemCount));
  } else if (command.startsWith("PZEM")) {
    handlePzem(parseSuffix(command, "PZEM"));
  } else if (command.startsWith("SETADDR")) {
    handleSetAddress(parseSuffix(command, "SETADDR"));
  } else if (command.startsWith("RELAYON")) {
    handleRelay(parseSuffix(command, "RELAYON"), true);
  } else if (command.startsWith("RELAYOFF")) {
    handleRelay(parseSuffix(command, "RELAYOFF"), false);
  } else {
    reply("ERROR:COMANDO_DESCONOCIDO");
  }
}

}  // namespace

void setup() {
  Serial.begin(kHostBaud);
  for (size_t i = 0; i < kPzemCount; ++i) {
    pzems[i] = new PZEM004Tv30(Serial2, kPzemRxPin, kPzemTxPin, kPzemAddresses[i]);
  }
  for (int pin : kRelayPins) {
    if (pin >= 0) {
      // Arrancar con el relé apagado
      digitalWrite(pin, kRelayActiveLow ? HIGH : LOW);
      pinMode(pin, OUTPUT);
    }
  }
  inputLine.reserve(kMaxLineLength);
  reply("LISTO:FW=" + String(kFirmwareVersion));
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      handleCommand(inputLine);
      inputLine = "";
    } else if (inputLine.length() < kMaxLineLength) {
      inputLine += c;
    }
  }
}
