title: DDN S2A: IO
agents: ddn_s2a
catalog: hw/storagehw/ddn_s2a
license: GPL
distribution: check_mk
description:
 This check monitors the number ofread and write IO operations.

item:
 The port number or "Total"

inventory:
 One service is created for each FC port and
 one service is created for the total IO.
