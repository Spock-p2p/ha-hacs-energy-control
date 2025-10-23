# Spock Energy Control

<p align="center">
  <img src="https://github.com/Spock-p2p/ha-hacs-energy-control/blob/main/logo.png" width="75"/>
</p>

**Control inteligente de dispositivos que permite pausarlos automáticamente según una señal remota de precios o consumo.**

- Dominio: `spock_energy_control`
- Endpoint fijo (no configurable): `https://flex.spock.es/api/status`
- La respuesta esperada es:
-   { "action": "stop" }  // apaga dispositivos seleccionados
-   {"action": "start" } // enciende dispositivos seleccionados
