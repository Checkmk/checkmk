#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# .------------------------------------------------------------------------.
# |                ____ _               _        __  __ _  __              |
# |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
# |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
# |              | |___| | | |  __/ (__|   <    | |  | | . \               |
# |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
# |                                        |_____|                         |
# |             _____       _                       _                      |
# |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
# |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
# |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
# |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
# |                                     |_|                                |
# |                     _____    _ _ _   _                                 |
# |                    | ____|__| (_) |_(_) ___  _ __                      |
# |                    |  _| / _` | | __| |/ _ \| '_ \                     |
# |                    | |__| (_| | | |_| | (_) | | | |                    |
# |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
# |                                                                        |
# | mathias-kettner.com                                 mathias-kettner.de |
# '------------------------------------------------------------------------'
#  This file is part of the Check_MK Enterprise Edition (CEE).
#  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
#  Distributed under the Check_MK Enterprise License.
#
#  You should have  received  a copy of the Check_MK Enterprise License
#  along with Check_MK. If not, email to mk@mathias-kettner.de
#  or write to the postal address provided at www.mathias-kettner.de

import cmk_base


def section_name_of(check_plugin_name):
    return check_plugin_name.split(".")[0]


def is_snmp_check(check_plugin_name):
    cache = cmk_base.runtime_cache.get_dict("is_snmp_check")
    try:
        return cache[check_plugin_name]
    except KeyError:
        snmp_checks = cmk_base.runtime_cache.get_set("check_type_snmp")
        result = section_name_of(check_plugin_name) in snmp_checks
        cache[check_plugin_name] = result
        return result


def is_tcp_check(check_plugin_name):
    cache = cmk_base.runtime_cache.get_dict("is_tcp_check")
    try:
        return cache[check_plugin_name]
    except KeyError:
        tcp_checks = cmk_base.runtime_cache.get_set("check_type_tcp")
        result = section_name_of(check_plugin_name) in tcp_checks
        cache[check_plugin_name] = result
        return result
