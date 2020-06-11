title: Rittal CMC-III IO Units: Status of Input and Output Ports
agents: snmp
catalog: hw/environment/rittal
license: GPL
distribution: check_mk
description:
 This check monitors the status of the Input and Output Ports of
 the Rittal CMC-III IO Units,
 No limits are set in the check.  The state given by the Rittal device is
 taken as the state of the check as follows:
 For input ports the state is {OK} when the value at the port is {0}.
 For output ports the state is {OK} when the status of the port is {Off}.
 Otherwise the checks are {WARN}.

item:
 The internal name of the input or output ports

inventory:
 One service is created for each input and output port.
