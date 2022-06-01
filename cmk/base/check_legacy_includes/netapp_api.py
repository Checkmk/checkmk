#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import host_extra_conf_merged, host_name
from cmk.base.plugins.agent_based.utils import netapp_api


# Transforms all lines into a dictionary.
# The first key is the dictionary key, unless modified by the custom_keys
def netapp_api_parse_lines(info, custom_keys=None, as_dict_list=False, item_func=None):
    if as_dict_list:
        return netapp_api.parse_netapp_api_multiple_instances(
            info,
            custom_keys=custom_keys,
            item_func=item_func,
        )
    return netapp_api.parse_netapp_api_single_instance(
        info,
        custom_keys=custom_keys,
        item_func=item_func,
    )


def discover_single_items(discovery_rules):
    config = host_extra_conf_merged(host_name(), discovery_rules)
    mode = config.get("mode", "single")
    return mode == "single"


def maybefloat(num):
    """Return a float, or None if not possible.

    :param num:
        Something numeric, either an integer a float or a string. Must be convertible
        via a call to `float`.

    :return:
        A float or None
    """
    try:
        return float(num)
    except (TypeError, ValueError):
        return None
