# Spock Energy Control

Integración para Home Assistant que gestiona dispositivos en función de una señal externa.

Cada 15 segundos consulta `https://flex.spock.es/api/status`, que devuelve:

{ "action": "stop" }
o
{ "action": "start" }
