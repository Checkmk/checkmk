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
 For each fan found on the appliance a service is created.

[parameters]
parameters(dict): parameters is a dictionary with two keys

 {"lower"}: a tuple of lower warning and critical levels for the fan rpm.

 {"upper"}: a tuple of upper warning and critical levels for the fan rpm.

 The numbers are integers.

[configuration]
netscaler_health_fan_default_levels(dict): This variable is preset to {{ "lower": (2000, 1000), "upper": (8000, 8400) }}

