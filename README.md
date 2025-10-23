# Spock Energy Control

![Logo](https://raw.githubusercontent.com/spockp2p/ha-hacs-energy-control/main/logo.png)

**Control inteligente de dispositivos que permite pausarlos automáticamente según una señal remota de precios o consumo.**

- Dominio: `spock_energy_control`
- Endpoint fijo (no configurable): `https://flex.spock.es/api/status`
- La respuesta esperada es:
-   { "action": "stop" }  // apaga dispositivos seleccionados
-   {"action": "start" } // enciende dispositivos seleccionados
