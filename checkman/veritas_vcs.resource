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
 - "OFFLINE|STATE UNKNOWN" or "ONLINE|STATE UNKNOWNEXITED" will be UNKNOWN.

 The check is cluster-aware. In this case we have:
 - If one resource reports "FAULTED" the service state will be CRIT,
 - if one reports "UNKNOWN" it will be UNKNOWN,
 - if one reports "ONLINE" the state will be OK,
 - if all resources are "OFFLINE" the service state will be CRIT,
 - otherwise it will be WARN.

item:
 The resource name.

inventory:
 One service per resource is created.
