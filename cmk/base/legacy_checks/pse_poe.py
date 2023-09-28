#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.poe import check_poe_data, PoeValues
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import exists, OIDEnd, SNMPTree

# We fetch the following columns from SNMP:
# 2 pethMainPsePower (The nominal power of the PSE expressed in Watts)
# 3 pethMainPseOperStatus (The operational status of the main PSE) (on(1), off(2), faulty(3))
# 4 pethMainPseConsumptionPower (Measured usage power expressed in Watts)


def parse_pse_poe(string_table):
    """
    parse string_table data and create dictionary with namedtuples for each OID.

    {
       oid_end : PoeValues(poe_max, poe_used, poe_status, poe_status_detail)
    }

    :param string_table: parsed snmp data
    :return: dictionary
    """
    poe_dict = {}
    for oid_end, poe_max, pse_op_status, poe_used in string_table:
        poe_dict[str(oid_end)] = PoeValues(
            poe_max=int(poe_max),
            poe_used=int(poe_used),
            poe_status=int(pse_op_status),
            poe_status_detail=None,
        )
    return poe_dict


def inventory_pse_poe(parsed):
    return [(oid_end, {}) for oid_end in parsed]


def check_pse_poe(item, params, parsed):
    if not (poe_data := parsed.get(item)):
        return
    yield check_poe_data(params, poe_data)


check_info["pse_poe"] = LegacyCheckDefinition(
    detect=exists(".1.3.6.1.2.1.105.1.3.1.1.*"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.105.1.3.1.1",
        oids=[OIDEnd(), "2", "3", "4"],
    ),
    parse_function=parse_pse_poe,
    service_name="POE%s consumption ",
    discovery_function=inventory_pse_poe,
    check_function=check_pse_poe,
    check_default_parameters={"levels": (90.0, 95.0)},
)
