#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Iterable, Optional
import string


# TODO: I know we already have SectionName in check_utils.py
#       However, this is a true class, not just a type alias.
#       Hopefully we can remove SectionName soon.
class PluginName:
    """Common class for all plugin names

    A plugin name must be a non-empty string consting only of letters A-z, digits
    and the underscore.
    """
    VALID_CHARACTERS = string.ascii_letters + '_' + string.digits

    # unfortunately, we have some WATO rules that contain dots or dashs.
    # In order not to break things, but be consistent in the future
    # we maintain a list of exceptions.
    _LEGACY_NAMING_EXCEPTIONS = {
        'drbd.net', 'drbd.disk', 'drbd.stats', 'fileinfo-groups', 'hpux_snmp_cs.cpu',
        'j4p_performance.mem', 'j4p_performance.threads', 'j4p_performance.uptime',
        'j4p_performance.app_state', 'j4p_performance.app_sess', 'j4p_performance.serv_req',
        'sap_value-groups'
    }

    def __init__(self, plugin_name, forbidden_names=None):
        # type: (str, Optional[Iterable[PluginName]]) -> None
        self._value = plugin_name
        if plugin_name in self._LEGACY_NAMING_EXCEPTIONS:
            return

        if not isinstance(plugin_name, str):
            raise TypeError("PluginName must initialized from str")
        if not plugin_name:
            raise ValueError("PluginName initializer must not be empty")

        for char in plugin_name:
            if char not in self.VALID_CHARACTERS:
                raise ValueError("invalid character for PluginName %r: %r" % (plugin_name, char))

        if forbidden_names and any(plugin_name == str(fn) for fn in forbidden_names):
            raise ValueError("duplicate plugin name: %r" % (plugin_name,))

    def __repr__(self):
        # type: () -> str
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def __str__(self):
        # type: () -> str
        return self._value

    def __eq__(self, other):
        # type: (Any) -> bool
        if not isinstance(other, self.__class__):
            raise TypeError("can only be compared with %s objects" % self.__class__)
        return self._value == other._value

    def __lt__(self, other):
        # type: (PluginName) -> bool
        if not isinstance(other, self.__class__):
            raise TypeError("Can only be compared with %s objects" % self.__class__)
        return self._value < other._value

    def __hash__(self):
        # type: () -> int
        return hash(self._value)
