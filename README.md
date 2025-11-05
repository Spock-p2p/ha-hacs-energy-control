# Control de Energía Spock (HACS) - Integración para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

Esta es una integración personalizada para [Home Assistant (HA)](https://www.home-assistant.io/) diseñada para recibir señales de control activas desde la plataforma en la nube de Spock.

** Para utilizar esta integración es imprescindible crear un cuenta en Spock: https://spock.es/register **

A diferencia de las integraciones de telemetría (que leen potencia, SOC, etc.), esta integración se enfoca en recibir **acciones** o **comandos** (ej. "iniciar carga", "detener descarga") generados por el EMS de Spock. Su propósito principal es permitirte crear automatizaciones complejas en Home Assistant basadas en estas señales.

## Características

* Se conecta al endpoint `/api/status` de Spock para obtener señales de control.
* Crea sensores binarios (on/off) para cada señal de control (ej. "green", "yellow").
* Permite disparar automatizaciones en Home Assistant basadas en el estado de estas señales.

---

## Instalación

### Método 1: HACS (Recomendado)

1.  Asegúrate de tener [HACS](https://hacs.xyz/) instalado en tu Home Assistant.
2.  Ve a la sección de HACS en tu panel de Home Assistant.
3.  Haz clic en "Integraciones".
4.  Haz clic en el menú de tres puntos en la esquina superior derecha y selecciona "Repositorios personalizados".
5.  En el campo "Repositorio", pega la URL de este repositorio: `https://github.com/Spock-p2p/ha-hacs-energy-control/`
6.  En la categoría, selecciona "Integración".
7.  Haz clic en "Añadir".
8.  Ahora deberías ver "Spock Energy Control" en tu lista de integraciones. Haz clic en "Instalar".
9.  Reinicia Home Assistant.

### Método 2: Instalación Manual

1.  Descarga la última versión ([release](https://github.com/Spock-p2p/ha-hacs-energy-control/releases)) de este repositorio.
2.  Descomprime el archivo.
3.  Copia la carpeta `spock_energy_control` (que se encuentra dentro de la carpeta `custom_components` del archivo ZIP) en el directorio `custom_components` de tu instalación de Home Assistant.
    * La ruta final debería ser: `<config_dir>/custom_components/spock_energy_control/`
4.  Reinicia Home Assistant.

---

## Configuración

No es necesario ningun paso adicional, a parte de los parámetros entrados en el momento de configuración del componente.
  
## Parámetros de Configuración

1.  plant_id (Requerido): El identificador único (plant_id) de tu instalación.
2.  auth_token (Requerido): El token de autenticación (X-Auth-Token) necesario para acceder a la API.
3.  scan_interval (Opcional): Frecuencia con la que se comprueban las señales. El valor por defecto es 30 segundos. Un valor más bajo permite una respuesta más rápida.

## Entidades Creadas
Esta integración creará los siguientes sensores binarios. Estarán en estado on cuando la acción sea "start" y off cuando sea "stop".

1.  binary_sensor.spock_action_green: Representa la señal de control "green".
2.  binary_sensor.spock_action_yellow: Representa la señal de control "yellow".

# Ejemplos de Automatización
El verdadero poder de esta integración está en usar estos sensores binarios para controlar otros dispositivos en Home Assistant.

## Ejemplo 1: Iniciar la carga de un vehículo eléctrico con la señal "green"
Esto encenderá un enchufe inteligente (ej. switch.cargador_vehiculo) cuando la señal "green" se active (pase a on).

```yaml
alias: 'EMS - Iniciar Carga Vehiculo con Señal Green'
description: 'Enciende el cargador del VE cuando el EMS de Spock da la señal green'
trigger:
  - platform: state
    entity_id: binary_sensor.spock_action_green
    to: 'on'
condition: []
action:
  - service: switch.turn_on
    target:
      entity_id: switch.cargador_vehiculo
mode: single
```

## Ejemplo 2: Detener un electrodoméstico con la señal "yellow"
Esto apagará un enchufe (switch.enchufe_termo) cuando la señal "yellow" se active (pase a on), y no lo volverá a encender hasta que la señal "yellow" se desactive (pase a off).

```yaml
alias: 'EMS - Gestionar Termo con Señal Yellow'
description: 'Apaga el termo si la señal yellow está activa'
trigger:
  - platform: state
    entity_id: binary_sensor.spock_action_yellow
    id: 'yellow_on'
    to: 'on'
  - platform: state
    entity_id: binary_sensor.spock_action_yellow
    id: 'yellow_off'
    to: 'off'
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id: 'yellow_on'
        sequence:
          - service: switch.turn_off
            target:
              entity_id: switch.enchufe_termo
      - conditions:
          - condition: trigger
            id: 'yellow_off'
        sequence:
          - service: switch.turn_on
            target:
              entity_id: switch.enchufe_termo
mode: single
```
