title: Bintec Routers: Fan Speed
agents: snmp
catalog: hw/network/bintec
license: GPL
distribution: check_mk
description:
 Checks the Fan Speed of Bintec Routers.

item:
 The sensorDescr from SNMP.

perfdata:
 None

inventory:
 For each fan one service is created

[parameters]
warn (int): Warning if speed is below
crit (int): Critical if speed is below
