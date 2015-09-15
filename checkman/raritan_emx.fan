title: Raritan EMX devices: Fan State and Speed
agents: snmp
catalog: hw/other
license: GPL
distribution: check_mk
description:
 Shows Sensor information for Fan state and speed
 for each Rack connected to a Raritan EMX devices.
 No configuration is needed, the devices sends the state by himself

item:
 Rack ID, Sensor Type, Sensor Name

inventory:
 One service per sensor will be created

