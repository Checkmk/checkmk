title: Citrix Netscaler Loadbalancer: Speed of Fans
agents: snmp
catalog: app/netscaler
license: GPL
distribution: check_mk
description:
 This check monitors the speed of fans on Citrix Netscaler Loadbalancing
 Appliances. It uses SNMP to scan the {nsSysHealthTable} in the NS-ROOT-MIB
 for fans and retrieves the rpm of the fans from this table.

 Upper and lower warning and critical levels to the fans' rpm can be configured.

item:
 The Name of the fan according to the {sysHealthname} in the {nsSysHealthTable}

inventory:
 One service is created for each fan found on the appliance.

