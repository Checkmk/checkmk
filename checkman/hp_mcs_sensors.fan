title: HPE MCS 200: Fan Status
agents: snmp
catalog: hw/environment/hpe
license: GPL
distribution: check_mk
description:

 This check monitors the speed of fans in MCS cooling devices. Thresholds
 are configureable throudh the regular fan rules.

item:
 Name of the sensor

inventory:
 One service is created for each fan sensor.
