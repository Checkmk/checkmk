title: Brocade NetIron MLX devices: Fans
agents: snmp
catalog: hw/network/brocade 
license: GPL
distribution: check_mk
description:
 Checks the operational status of fans in Brocade NetIron MLX
 switching / routing devices.

 Returns {OK} on status 2 (normal), {CRIT} on status 3 (failure)
 and {UNKN} on every other status.

item:
 If a fan description is delivered by SNMP, the item is build from the 
 fan ID plus the description. Otherwise it is just the ID.

inventory:
 Finds one item per fan.
