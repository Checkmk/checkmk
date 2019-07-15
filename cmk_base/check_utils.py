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

from typing import Union, TypeVar, Iterable, Text, Optional, Dict, Tuple, Any, List  # pylint: disable=unused-import

from cmk.utils.exceptions import MKGeneralException

import cmk_base
from cmk_base.discovered_labels import DiscoveredServiceLabels

Item = Union[Text, None, int]
CheckParameters = Union[None, Dict, Tuple, List, str]
CheckPluginName = str
CheckTable = Dict[Tuple[CheckPluginName, Item], Tuple[Any, Text, List[Text]]]


class Service(object):
    __slots__ = ["_check_plugin_name", "_item", "_description", "_parameters", "_service_labels"]

    def __init__(self, check_plugin_name, item, description, parameters, service_labels=None):
        # type: (CheckPluginName, Item, Text, CheckParameters, DiscoveredServiceLabels) -> None
        self._check_plugin_name = check_plugin_name
        self._item = item
        self._description = description
        self._parameters = parameters
        self._service_labels = service_labels or DiscoveredServiceLabels()

    @property
    def check_plugin_name(self):
        return self._check_plugin_name

    @property
    def item(self):
        return self._item

    @property
    def description(self):
        return self._description

    @property
    def parameters(self):
        return self._parameters

    @property
    def service_labels(self):
        return self._service_labels

    def __eq__(self, other):
        """Is used during service discovery list computation to detect and replace duplicates
        For this the parameters and similar need to be ignored."""
        return self.check_plugin_name == other.check_plugin_name and self.item == other.item

    def __hash__(self):
        """Is used during service discovery list computation to detect and replace duplicates
        For this the parameters and similar need to be ignored."""
        return hash((self.check_plugin_name, self.item))


class DiscoveredService(Service):
    """Special form of Service() which holds the unresolved textual representation of the check parameters"""
    __slots__ = ["_check_plugin_name", "_item", "_description", "_parameters", "_service_labels"]

    def __init__(self, check_plugin_name, item, description, paramstr, service_labels=None):
        # type: (CheckPluginName, Item, Text, CheckParameters, DiscoveredServiceLabels) -> None
        super(DiscoveredService, self).__init__(check_plugin_name=check_plugin_name,
                                                item=item,
                                                description=description,
                                                parameters=paramstr,
                                                service_labels=service_labels)

    @property
    def parameters(self):
        raise MKGeneralException(
            "Can not get the resolved parameters from a DiscoveredService object")

    @property
    def paramstr(self):
        return self._parameters


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
