title: Brocade FibreChannel Switches: Fans
catalog: hw/storagehw/brocade
agents: snmp
license: GPL
distribution: check_mk
description:
 This checks monitors the FAN speeds of a Brocade FC switch.

item:
 The number of the FAN (1, 2, 3 ...) as described in the SNMP output.

inventory:

 The inventory creates a service for each fan unless it is marked as absent
 in {swSensorStatus}


