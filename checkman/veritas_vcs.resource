title: Veritas Cluster Service: Resource
agents: linux
catalog: os/services
license: GPL
distribution: check_mk
description:
 This check needs the {check_mk_agent.linux} agent which provides
 information about the Veritas Cluster Service if it is installed.

 The check monitors the resource state and can have the following states:
 - "ONLINE" will be OK,
 - "OFFLINE" will be WARN,
 - "FAULTED" will be "CRIT",
 - "OFFLINE|STATE UNKNOWN" or "ONLINE|STATE UNKNOWNEXITED" will be UNKNOWN,
 - all others will be WARN.

 The check is cluster-aware. In this case:
 - if all service groups report the same, that state is used,
 - if any service group reports "FAULTED", "UNKNOWN", "ONLINE" or
   "RUNNING", the respective state will be used (checked in that order)
 - otherwise the states will be concatenated.

item:
 The resource name.

inventory:
 One service per resource is created.
