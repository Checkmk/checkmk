title: HPE MCS 200: Fan status
agents: snmp
catalog: hw/environment/hpe
license: GPL
distribution: check_mk
description:

 This check monitors the speed of fans in MCS cooling devices. Thresholds
 are configureable throudh the regular fan rules.


inventory:
 One service for each fan sensor will be created.
