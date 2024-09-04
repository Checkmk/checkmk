#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \ 
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  / 
#  ____) |    \  /\  /    | | \ \ 
# |_____/      \/  \/     |_|  \_\
#
# (c) 2024 SWR
# @author Frank Baier <frank.baier@swr.de>
#
#
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register,
    Service,
    Result,
    State,
    SNMPTree,
    contains,
    any_of,
)


def discover_cisco_ucs_fault(section):
    yield Service()


def check_cisco_ucs_fault(section):
    no_error=True

    for (cucsFaultDn, cucsFaultRn, cucsFaultAffectedObjectId, cucsFaultAffectedObjectDn, cucsFaultAck,
    cucsFaultProbableCause, cucsFaultChangeSet, cucsFaultCode, cucsFaultCreationTime, 
    cucsFaultDescription, cucsFaultHighestSeverity, cucsFaultId, cucsFaultLastModificationTime, 
    cucsFaultLc, cucsFaultOccur, cucsFaultOrigSeverity, cucsFaultPrevSeverity, cucsFaultRule, 
    cucsFaultSeverity, cucsFaultTags, cucsFaultType) in section[0]:

        no_error=False
        yield Result(state=State.CRIT, summary="%s" % cucsFaultDescription)

    if no_error:
        yield Result(state=State.OK, summary="No faults detected")

'''
cucsFaultIndex 	1.3.6.1.4.1.9.9.719.1.1.1.1.1
Instance identifier of the managed object.
Status: current 	Access: not-accessible
OBJECT-TYPE 		  	 
  	CucsManagedObjectId 		 

cucsFaultDn 	1.3.6.1.4.1.9.9.719.1.1.1.1.2
Cisco UCS fault:Inst:dn managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsManagedObjectDn 		 

cucsFaultRn 	1.3.6.1.4.1.9.9.719.1.1.1.1.3
Cisco UCS fault:Inst:rn managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	SnmpAdminString 		 

cucsFaultAffectedObjectId 	1.3.6.1.4.1.9.9.719.1.1.1.1.4
Cisco UCS fault:Inst:affectedObjectId managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	RowPointer 		 

cucsFaultAffectedObjectDn 	1.3.6.1.4.1.9.9.719.1.1.1.1.5
Cisco UCS fault:Inst:affectedObjectDn managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsManagedObjectDn 		 

cucsFaultAck 	1.3.6.1.4.1.9.9.719.1.1.1.1.6
Cisco UCS fault:Inst:ack managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	TruthValue 		 

cucsFaultProbableCause 	1.3.6.1.4.1.9.9.719.1.1.1.1.7
Cisco UCS fault:Inst:cause managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultProbableCause 		 

cucsFaultChangeSet 	1.3.6.1.4.1.9.9.719.1.1.1.1.8
Cisco UCS fault:Inst:changeSet managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	SnmpAdminString 		 

cucsFaultCode 	1.3.6.1.4.1.9.9.719.1.1.1.1.9
Cisco UCS fault:Inst:code managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultCode 		 

cucsFaultCreationTime 	1.3.6.1.4.1.9.9.719.1.1.1.1.10
Cisco UCS fault:Inst:created managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	DateAndTime 		 

cucsFaultDescription 	1.3.6.1.4.1.9.9.719.1.1.1.1.11
Cisco UCS fault:Inst:descr managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	SnmpAdminString 		 

cucsFaultHighestSeverity 	1.3.6.1.4.1.9.9.719.1.1.1.1.12
Cisco UCS fault:Inst:highestSeverity managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultSeverity 		 

cucsFaultId 	1.3.6.1.4.1.9.9.719.1.1.1.1.13
Cisco UCS fault:Inst:id managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	Unsigned64 		 

cucsFaultLastModificationTime 	1.3.6.1.4.1.9.9.719.1.1.1.1.14
Cisco UCS fault:Inst:lastTransition managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	DateAndTime 		 

cucsFaultLc 	1.3.6.1.4.1.9.9.719.1.1.1.1.15
Cisco UCS fault:Inst:lc managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsConditionLifecycle 		 

cucsFaultOccur 	1.3.6.1.4.1.9.9.719.1.1.1.1.16
Cisco UCS fault:Inst:occur managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	Counter32 		 

cucsFaultOrigSeverity 	1.3.6.1.4.1.9.9.719.1.1.1.1.17
Cisco UCS fault:Inst:origSeverity managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultSeverity 		 

cucsFaultPrevSeverity 	1.3.6.1.4.1.9.9.719.1.1.1.1.18
Cisco UCS fault:Inst:prevSeverity managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultSeverity 		 

cucsFaultRule 	1.3.6.1.4.1.9.9.719.1.1.1.1.19
Cisco UCS fault:Inst:rule managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsConditionRule 		 

cucsFaultSeverity 	1.3.6.1.4.1.9.9.719.1.1.1.1.20
Cisco UCS fault:Inst:severity managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultSeverity 		 

cucsFaultTags 	1.3.6.1.4.1.9.9.719.1.1.1.1.21
Cisco UCS fault:Inst:tags managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsConditionTag 		 

cucsFaultType 	1.3.6.1.4.1.9.9.719.1.1.1.1.22
Cisco UCS fault:Inst:type managed object property
Status: current 	Access: read-only
OBJECT-TYPE 		  	 
  	CucsFaultType 		 

.1.3.6.1.4.1.9.9.719.1.1.1.1.2.486542084 sys/rack-unit-1/fan-module-1-6/fan-1/fault-F0397
.1.3.6.1.4.1.9.9.719.1.1.1.1.3.486542084 F0397
.1.3.6.1.4.1.9.9.719.1.1.1.1.4.486542084 .1.3.6.1.4.1.9.9.719.1.15.12.1
.1.3.6.1.4.1.9.9.719.1.1.1.1.5.486542084 sys/rack-unit-1/fan-module-1-6/fan-1
.1.3.6.1.4.1.9.9.719.1.1.1.1.6.486542084 1
.1.3.6.1.4.1.9.9.719.1.1.1.1.7.486542084 381
.1.3.6.1.4.1.9.9.719.1.1.1.1.8.486542084 unknown
.1.3.6.1.4.1.9.9.719.1.1.1.1.9.486542084 397
.1.3.6.1.4.1.9.9.719.1.1.1.1.10.486542084 "07 E7 0C 0F 03 2D 0E 00 "
.1.3.6.1.4.1.9.9.719.1.1.1.1.11.486542084 MOD6_FAN1_SPEED: Fan speed for fan-11 is lower non recoverable : Check the air intake to the server 
.1.3.6.1.4.1.9.9.719.1.1.1.1.12.486542084 6
.1.3.6.1.4.1.9.9.719.1.1.1.1.13.486542084 486542084
.1.3.6.1.4.1.9.9.719.1.1.1.1.14.486542084 "07 E7 0C 0F 03 2D 0E 00 "
.1.3.6.1.4.1.9.9.719.1.1.1.1.15.486542084 0
.1.3.6.1.4.1.9.9.719.1.1.1.1.16.486542084 1
.1.3.6.1.4.1.9.9.719.1.1.1.1.17.486542084 6
.1.3.6.1.4.1.9.9.719.1.1.1.1.18.486542084 5
.1.3.6.1.4.1.9.9.719.1.1.1.1.19.486542084 397
.1.3.6.1.4.1.9.9.719.1.1.1.1.20.486542084 6
.1.3.6.1.4.1.9.9.719.1.1.1.1.21.486542084 "00 "
.1.3.6.1.4.1.9.9.719.1.1.1.1.22.486542084 5
'''
register.snmp_section(
    name="cisco_ucs_fault",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.719.1.1.1.1",
            oids=["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22"]),
    ],
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1682"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1683"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1684"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1685"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2178"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2179"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2424"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2492"),
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2493"),
    ),
)

register.check_plugin(
    name="cisco_ucs_fault",
    sections=["cisco_ucs_fault"],
    service_name="UCS Faults",
    discovery_function=discover_cisco_ucs_fault,
    check_function=check_cisco_ucs_fault,
)

