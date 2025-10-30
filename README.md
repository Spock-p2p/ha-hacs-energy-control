# Spock Energy Control V1.0.1

**Control inteligente de dispositivos que permite pausarlos automáticamente según una señal remota de precios o consumo.**
**Spock EMS para sistemas de almacenamiento (Marstek, SMA, ...)**

*Spock_energy_control*
- Endpoint fijo (no configurable): `https://flex.spock.es/api/status`
- La respuesta esperada es:
-   { "action": "stop" }  // apaga dispositivos seleccionados
-   {"action": "start" } // enciende dispositivos seleccionados

*Spock EMS*
- Endpoint fijo (no configurable): `https://flex.spock.es/api/ems`
- La respuesta esperada es la operación que tiene que realizar la batería, en función del modelo creado en Spock. Se tienen en cuenta, entre otras variables:
  - Modelo en IA que predice el consumo de la instalación
  - Modelo de predicción de producción fotovoltaica
  - Precios de la energía de la instalación
