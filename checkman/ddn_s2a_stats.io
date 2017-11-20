title: DDN S2A: IO
agents: ddn_s2a
catalog: storage/other
license: GPL
distribution: check_mk
description:
 This check monitors the number ofread and write IO operations.

item:
 The port number or "Total"

inventory:
 One service per FC port is created, plus one for the total IO.
