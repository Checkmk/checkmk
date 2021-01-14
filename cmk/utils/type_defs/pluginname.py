#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import string
from typing import Any, Set

__all__ = [
    "ABCName",
    "ParsedSectionName",
    "SectionName",
    "RuleSetName",
    "CheckPluginName",
    "InventoryPluginName",
]


class ABCName(abc.ABC):
    """Common class for all names.

    A plugin name must be a non-empty string consisting only of letters A-z, digits
    and the underscore.
    """
    VALID_CHARACTERS = string.ascii_letters + '_' + string.digits

    @abc.abstractproperty
    def _legacy_naming_exceptions(self) -> Set[str]:
        """we allow to maintain a list of exceptions"""
        return set()

    def __init__(self, plugin_name: str) -> None:
        self._value = plugin_name
        if plugin_name in self._legacy_naming_exceptions:
            return

        if not isinstance(plugin_name, str):
            raise TypeError("%s must initialized from str" % self.__class__.__name__)
        if not plugin_name:
            raise ValueError("%s initializer must not be empty" % self.__class__.__name__)

        for char in plugin_name:
            if char not in self.VALID_CHARACTERS:
                raise ValueError("invalid character for %s %r: %r" %
                                 (self.__class__.__name__, plugin_name, char))

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %r and %r" % (self, other))
        return self._value == other._value

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError("Can only be compared with %s objects" % self.__class__)
        return self._value < other._value

    def __le__(self, other: Any) -> bool:
        return self < other or self == other

    def __gt__(self, other: Any) -> bool:
        return not self <= other

    def __ge__(self, other: Any) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return hash(type(self).__name__ + self._value)


class ParsedSectionName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()


class SectionName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()


class RuleSetName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return {
            'drbd.net', 'drbd.disk', 'drbd.stats', 'fileinfo-groups', 'hpux_snmp_cs.cpu',
            'j4p_performance.mem', 'j4p_performance.threads', 'j4p_performance.uptime',
            'j4p_performance.app_state', 'j4p_performance.app_sess', 'j4p_performance.serv_req'
        }


class CheckPluginName(ABCName):
    MANAGEMENT_PREFIX = 'mgmt_'

    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()

    def is_management_name(self) -> bool:
        return self._value.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> 'CheckPluginName':
        if self.is_management_name():
            return self
        return CheckPluginName("%s%s" % (self.MANAGEMENT_PREFIX, self._value))

    def create_basic_name(self) -> 'CheckPluginName':
        if self.is_management_name():
            return CheckPluginName(self._value[len(self.MANAGEMENT_PREFIX):])
        return self


class InventoryPluginName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()
