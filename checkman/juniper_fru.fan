title: Juniper Ethernet Switch: Fan
agents: snmp
catalog: hw/network/juniper
license: GPL
distribution: check_mk
description:
 This check monitors the fans of a Juniper Ethernet Switch Chassis.

 The state of the service is given by the device itself:
 - present, ready, announce online, online OK
 - diagnostic, standby: WARN
 - empty, announce offline, offline: CRIT
 - unknown: UNKNOWN

item:
 The name of the power supply.

inventory:
 One service per power supply is created.
