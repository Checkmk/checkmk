title: Perle Mediaconverter: Fan status
agents: snmp
catalog: hw/app/perle
license: GPL
distribution: check_mk
description:
 This check monitors the fan status of the power supplies of
 Perle Meadiconverter devices which support the PERLE-MCR-MGT MIB.

 The check is OK, if the status is good, otherwise CRIT.

item:
 The fan identifier.

inventory:
 One service per fan is created.
