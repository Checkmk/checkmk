#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NewType, TypedDict

HostName = NewType("HostName", str)

NotificationType = Literal[
    "ACKNOWLEDGEMENT",
    "DOWNTIMECANCELLED",
    "DOWNTIMEEND",
    "DOWNTIMESTART",
    "FLAPPINGDISABLED",
    "FLAPPINGSTART",
    "FLAPPINGSTOP",
    "PROBLEM",
    "RECOVERY",
]


class EventContext(TypedDict, total=False):
    """Used to be dict[str, Any]"""

    CONTACTNAME: str
    CONTACTS: str
    DATE: str
    EC_COMMENT: str
    EC_FACILITY: str
    EC_PRIORITY: str
    EC_RULE_ID: str
    HOSTATTEMPT: str
    HOSTCONTACTGROUPNAMES: str
    HOSTGROUPNAMES: str
    HOSTNAME: HostName
    HOSTNOTIFICATIONNUMBER: str
    HOSTOUTPUT: str
    HOSTSTATE: Literal["UP", "DOWN", "UNREACHABLE"]
    HOSTTAGS: str
    HOST_SL: str
    LASTHOSTSTATE: str
    LASTHOSTSTATECHANGE: str
    LASTHOSTUP: str
    LASTSERVICEOK: str
    LASTSERVICESTATE: str
    LASTSERVICESTATECHANGE: str
    LOGDIR: str
    LONGDATETIME: str
    LONGSERVICEOUTPUT: str
    MICROTIME: str
    MONITORING_HOST: str
    NOTIFICATIONCOMMENT: str
    NOTIFICATIONTYPE: NotificationType
    OMD_ROOT: str
    OMD_SITE: str
    PREVIOUSHOSTHARDSTATE: str
    PREVIOUSSERVICEHARDSTATE: str
    SERVICEATTEMPT: str
    SERVICECHECKCOMMAND: str
    SERVICECONTACTGROUPNAMES: str
    SERVICEDESC: str
    SERVICEFORURL: str
    SERVICEGROUPNAMES: str
    SERVICENOTIFICATIONNUMBER: str
    SERVICEOUTPUT: str
    SERVICESTATE: str
    SHORTDATETIME: str
    SVC_SL: str
    WHAT: Literal["SERVICE", "HOST"]


class EnrichedEventContext(EventContext, total=False):
    # Dynamically added:
    # FOOSHORTSTATE: str
    # HOSTLABEL_*: str
    # SERVICELABEL_*: str

    # Dynamically added:
    # # Add short variants for state names (at most 4 characters)
    # for key, value in list(raw_context.items()):
    #     if key.endswith("STATE"):
    #         raw_context[key[:-5] + "SHORTSTATE"] = value[:4]
    # We know of:
    HOSTFORURL: str
    HOSTURL: str
    HOSTSHORTSTATE: str
    LASTHOSTSHORTSTATE: str
    LASTHOSTSTATECHANGE_REL: str
    LASTHOSTUP_REL: str
    LASTSERVICESHORTSTATE: str
    LASTSERVICESTATECHANGE_REL: str
    LASTSERVICEOK_REL: str
    PREVIOUSHOSTHARDSHORTSTATE: str
    PREVIOUSSERVICEHARDSHORTSTATE: str
    SERVICESHORTSTATE: str
    SERVICEURL: str
