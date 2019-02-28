title: ENTITY-SENSORS MIB: Fan Speed RPM
agents: snmp
catalog: hw/environment/palo_alto
license: GPL
distribution: check_mk
description:
 This check monitors the temperature of devices
 which support the ENTITY-SENSORS MIB such as
 Palo Alto Networks Series 200/3000.

 The lower default levels are set to 2000, 1000 RPM.
 The upper and lower levels are configurable.

item:
 The name or index of the sensor.

inventory:
 One service per sensor is created.
