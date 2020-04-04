title: OpenBSD Devices: Fan
agents: snmp, openbsd
catalog: os/hardware
license: GPL
distribution: check_mk

description:
 This check monitors the state of {{fan sensors}} in a hardware system running
 OpenBSD if this data is provided by SNMP.  These Services are using the
 standard values for warn/crit and are configurable like other checks of
 the same type.

item:
 The description of the sensor.

inventory:
 One service is created for each sensor with the correct sensor type ("fan").
