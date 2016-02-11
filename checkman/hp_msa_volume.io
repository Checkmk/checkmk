title: HP MSA 2040: Volume IO
agents: linux
catalog: hw/storagehw/hp
license: GPL
distribution: check_mk
description:
 This check monitors the IO summary of all volume of a HP MSA 2040 storage system.
 To make it work you have to configure the hp_msa datasource program via WATO.
 With the WATO rule "Discovery mode for Disk IO check" the check
 monitors each volume IO.

 The levels are configurable.

 No default levels are set.

item:
 The IO summary or the volume identifier.

inventory:
 One service for the summary or one service per volume is created
