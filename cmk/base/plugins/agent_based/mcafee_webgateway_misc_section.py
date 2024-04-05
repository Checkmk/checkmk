#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""
import datetime

from cmk.base.plugins.agent_based.agent_based_api import v1

from cmk.plugins.lib import mcafee_gateway


def parse_webgateway_misc(
    string_table: v1.type_defs.StringTable,
) -> mcafee_gateway.Section | None:
    if not string_table:
        return None
    # -- Miscellaneous (these counter are NO lifetime counter; they show the actual number)
    # .1.3.6.1.4.1.1230.2.7.2.5.2.0 16 --> MCAFEE-MWG-MIB::stClientCount.0
    # .1.3.6.1.4.1.1230.2.7.2.5.3.0 35 --> MCAFEE-MWG-MIB::stConnectedSockets.0
    clients_str, sockets_str, time_dns_str, time_engine_str = string_table[0]
    return mcafee_gateway.Section(
        client_count=int(clients_str) if clients_str.isdigit() else None,
        socket_count=int(sockets_str) if sockets_str.isdigit() else None,
        time_to_resolve_dns=(
            datetime.timedelta(milliseconds=int(time_dns_str)) if time_dns_str.isdigit() else None
        ),
        time_consumed_by_rule_engine=(
            datetime.timedelta(milliseconds=int(time_engine_str))
            if time_engine_str.isdigit()
            else None
        ),
    )


v1.register.snmp_section(
    name="mcafee_webgateway_misc",
    parsed_section_name="webgateway_misc",
    parse_function=parse_webgateway_misc,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.2.5",
        oids=[
            "2",  # MCAFEE-MWG-MIB::stClientCount
            "3",  # MCAFEE-MWG-MIB::stConnectedSockets
            "6",  # MCAFEE-MWG-MIB::stResolveHostViaDNS
            "7",  # MCAFEE-MWG-MIB::stTimeConsumedByRuleEngine
        ],
    ),
    detect=mcafee_gateway.DETECT_MCAFEE_WEBGATEWAY,
)

v1.register.snmp_section(
    name="skyhigh_security_webgateway_misc",
    parsed_section_name="webgateway_misc",
    parse_function=parse_webgateway_misc,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.59732.2.7.2.5",
        oids=[
            "2",  # ::stClientCount
            "3",  # ::stConnectedSockets
            "6",  # ::stResolveHostViaDNS
            "7",  # ::stTimeConsumedByRuleEngine
        ],
    ),
    detect=mcafee_gateway.DETECT_SKYHIGH_WEBGATEWAY,
)
