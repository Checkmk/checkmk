title: Bintec Routers: Fan Speed
agents: snmp
catalog: hw/network/bintec
license: GPL
distribution: check_mk
description:
 Checks the Fan Speed of Bintec Routers.

 Returns {WARN} or {CRIT} if the speed is above or equal given levels or it is
 below or equal given levels.

item:
 The sensorDescr from SNMP.

examples:
 # set new default levels
 bintec_sensors_fan_default_levels = { "lower": ( 1, 1000), "upper": (9000, 10000) }

 # check Fan 1 of router1 with default levels
 checks += [
    ("router1", "bintec_sensors.fan", 'Fan 1', bintec_sensors_fan_default_levels)
 ]

perfdata:
 One value: The speed of the fan in rpm, together with the upper and lower
 levels for {WARN} and {CRIT}.

inventory:
 Creates one check per fan, concrete: One check for every sensor of sensorType 2
 (fan).

[parameters]
dict: key "lower" references a tuple with lower crit level and lower warn level.
 key "upper" references a tuple with upper warn level and upper crit level.

[configuration]
bintec_sensors_fan_default_levels (dict): 
 defaults to { "lower": ( 1000, 2000), "upper": (8000, 8400)
