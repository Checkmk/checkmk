#!/usr/bin/python
# encoding: utf-8

aggregation_rules["host"] = (
  "Host $HOST$",
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", HOST_STATE ),
      ( "filesystems",  [ "$HOST$" ] ),
      ( "cpuandmem",    [ "$HOST$" ] ),
      ( "networking",   [ "$HOST$" ] ),
      ( "checkmk",      [ "$HOST$" ] ),
      ( "applications", [ "$HOST$" ] ),
      ( "logfiles",     [ "$HOST$" ] ),
      ( "hardware",     [ "$HOST$" ] ),
      ( "other",        [ "$HOST$" ] ),
  ]
)

aggregation_rules["filesystems"] = (
  "Filesystems", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "fs_" ),
      ( "$HOST$", "Mount|Disk" ),
      ( "multipathing", [ "$HOST$" ]),
  ]
)

aggregation_rules["multipathing"] = (
  "Multipathing", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "Multipath" ),
  ]
)

aggregation_rules["cpuandmem"] = (
  "CPU, Kernel, Memory", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "CPU|Memory|Kernel|Number of threads" ),
  ]
)

aggregation_rules["hardware"] = (
  "Hardware", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "IPMI|RAID" ),
  ]
)

aggregation_rules["networking"] = (
  "Networking", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "NFS" ),
      ( FOREACH, "$HOST$", "NIC ([a-z]*).* counters", "nic", [ "$HOST$", "$1$" ] ),
  ]
)

aggregation_rules["nic"] = (
  "NIC $NIC$", 
  [ "HOST", "NIC" ],
  "worst",
  [
      ( "$HOST$", "NIC $NIC$" ),
  ]
)

aggregation_rules["checkmk"] = (
  "Check_MK", 
  [ "HOST" ],
  "worst",
  [
       ( "$HOST$", "Check_MK|Uptime" ),
  ]
)

aggregation_rules["logfiles"] = (
  "Logfiles", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "LOG" ),
  ]
)
aggregation_rules["applications"] = (
  "Applications", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", "ASM|ORACLE|proc" ),
  ]
)

aggregation_rules["other"] = (
  "Other", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", REMAINING ),
  ]
)

aggregations += [
  ( "Hosts", FOREACH, "(.*)", "Check_MK$", "host", ["$1$"] ),
]

