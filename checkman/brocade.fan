title: Brocade FibreChannel Switches: Fans
catalog: hw/storagehw/brocade
agents: snmp
license: GPL
distribution: check_mk
description:
 This checks monitors the FAN speeds of a Brocade FC switch.

item:
 The number of the FAN (1, 2, 3 ...) like descripted in the SNMP output.

perfdata:
 The speed of each fan.

inventory:
 The inventory creates a service for each fan.

[parameters]
warn(int): the minimum fan speed for an OK state
crit(int): the minimum fan speed for a WARN state

