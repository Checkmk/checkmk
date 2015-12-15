title: Avaya 88xx Chassis Fans
agents: snmp
catalog: hw/network/avaya
license: GPL
distribution: check_mk
description:
 This check monitors the fan status of Avaya 88xx devices.
 Depending on the reported state it can go OK, UNKNOWN or DOWN.

item:
 The index of the chassis fan.

inventory:
 Creates one service for each chassis fan.
