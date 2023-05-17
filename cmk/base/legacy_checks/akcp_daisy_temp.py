#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from itertools import chain

from cmk.base.check_api import all_of, any_of, equals, exists, LegacyCheckDefinition, not_exists
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree

factory_settings["akcp_daisy_temp_defaultlevels"] = {"levels": (28.0, 32.0)}


def inventory_akcp_daisy_temp(info):
    for _port, subport, name, _temp in chain.from_iterable(info):
        # Ignore sensors that are found by the non-daisychaining-version of
        # this check (akcp_sensor_temp)
        if subport not in ["-1", "0"]:
            yield name, {}


def check_akcp_daisy_temp(item, params, info):
    for _port, _subport, name, rawtemp in chain.from_iterable(info):
        if name == item:
            temp = float(rawtemp) / 10
            return check_temperature(temp, params, "akcp_daisy_temp_%s" % item)
    return None


check_info["akcp_daisy_temp"] = LegacyCheckDefinition(
    detect=all_of(
        any_of(
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854.1.2.2.1.1"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3854.1"),
        ),
        not_exists(".1.3.6.1.4.1.3854.2.*"),
        exists(".1.3.6.1.4.1.3854.1.2.2.1.19.*"),
    ),
    check_function=check_akcp_daisy_temp,
    discovery_function=inventory_akcp_daisy_temp,
    service_name="Temperature %s",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.1.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.2.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.3.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.4.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.5.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.6.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.7.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3854.1.2.2.1.19.33.8.2.1",
            oids=[OIDEnd(), "1", "2", "14"],
        ),
    ],
    check_ruleset_name="temperature",
    default_levels_variable="akcp_daisy_temp_defaultlevels",
    check_default_parameters={"levels": (28.0, 32.0)},
)
