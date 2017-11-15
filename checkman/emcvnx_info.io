title: EMC VNX Storage: Info about IO
agents: emc
catalog: hw/storagehw/emc
license: GPL
distribution: check_mk
description:
 Reports information about IO statistics like maximum requests, average
 requests, and total read.

 This subcheck returns the status {CRIT} if hard errors exist. Otherwise
 the status {OK} is returned.

 The information is retrieved by the special agent agent_emcvnx which uses
 EMC's command line tool naviseccli.

item:
 No item.

inventory:
 Finds exactly one item on every EMC VNX storage system called EMC VNX IO
