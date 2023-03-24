#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils import netapp_api


def get_and_try_cast_to_int(key: str, container: dict, default_value: int | None = None) -> int:
    try:
        to_be_casted = (
            container.get(key, default_value) if default_value is not None else container[key]
        )
        return int(to_be_casted)
    except ValueError as e:
        # Some NetApp firmware versions return corrupt data.
        # Known reported tickets (among others):
        # SUP-9508, SUP-5407, SUP-6805
        raise RuntimeError(
            "Unable to cast the data to integer. "
            "The reason therfore may be an issue in the used NetApp Firmware. "
            "Consider upgrading and/or getting in touch with NetApp."
            "Received data was: %s" % to_be_casted
        ) from e


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
