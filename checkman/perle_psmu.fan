title: Perle Mediaconverter: Fan Status
agents: snmp
catalog: hw/network/perle
license: GPL
distribution: check_mk
description:
 This check monitors the fan status of the power supplies of
 Perle Meadiconverter devices which support the PERLE-MCR-MGT MIB.

 The check is OK, if the status is good, otherwise CRIT.

item:
 The fan identifier.

inventory:
 One service is created for each fan.
