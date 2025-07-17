#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import string
from typing import Final, NamedTuple

from ._misc import Item

__all__ = [
    "ABCName",
    "ParsedSectionName",
    "SectionName",
    "RuleSetName",
    "CheckPluginName",
    "InventoryPluginName",
    "ServiceID",
]


class ABCName(abc.ABC):
    """Common class for all names.

    A plugin name must be a non-empty string consisting only of letters A-z, digits
    and the underscore.
    """

    VALID_CHARACTERS = string.ascii_letters + "_" + string.digits

    @classmethod
    @abc.abstractmethod
    def _legacy_naming_exceptions(cls) -> set[str]:
        """we allow to maintain a list of exceptions"""
        raise NotImplementedError()

    @classmethod
    def _validate_args(cls, plugin_name: str) -> str:
        if plugin_name in cls._legacy_naming_exceptions():
            return plugin_name

        if not isinstance(plugin_name, str):
            raise TypeError(f"{cls.__name__} must initialized from str")
        if not plugin_name:
            raise ValueError(f"{cls.__name__} initializer must not be empty")

        if any(c not in cls.VALID_CHARACTERS for c in plugin_name):
            invalid = "".join(c for c in plugin_name if c not in cls.VALID_CHARACTERS)
            raise ValueError(
                f"Invalid characters in {plugin_name!r} for {cls.__name__}: {invalid!r}"
            )

        return plugin_name

    def __getnewargs__(self) -> tuple[str]:
        return (str(self),)

    def __new__(cls, plugin_name: str) -> ABCName:
        cls._validate_args(plugin_name)
        return super().__new__(cls)

    def __init__(self, plugin_name: str) -> None:
        self._value: Final = plugin_name
        self._hash: Final = hash(type(self).__name__ + self._value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._value == other._value

    def __lt__(self, other: ABCName) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._value < other._value

    def __le__(self, other: ABCName) -> bool:
        return self < other or self == other

    def __gt__(self, other: ABCName) -> bool:
        return not self <= other

    def __ge__(self, other: ABCName) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return self._hash


class ParsedSectionName(ABCName):
    @classmethod
    def _legacy_naming_exceptions(cls) -> set[str]:
        return set()


class SectionName(ABCName):
    @classmethod
    def _legacy_naming_exceptions(cls) -> set[str]:
        return set()


class RuleSetName(ABCName):
    @classmethod
    def _legacy_naming_exceptions(cls) -> set[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return {
            "drbd.net",
            "drbd.disk",
            "drbd.stats",
            "fileinfo-groups",
            "hpux_snmp_cs.cpu",
            "j4p_performance.mem",
            "j4p_performance.threads",
            "j4p_performance.uptime",
            "j4p_performance.app_state",
            "j4p_performance.app_sess",
            "j4p_performance.serv_req",
        }


class CheckPluginName(ABCName):
    MANAGEMENT_PREFIX = "mgmt_"

    @classmethod
    def _legacy_naming_exceptions(cls) -> set[str]:
        return set()

    def is_management_name(self) -> bool:
        return self._value.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> CheckPluginName:
        if self.is_management_name():
            return self
        return CheckPluginName(f"{self.MANAGEMENT_PREFIX}{self._value}")

    def create_basic_name(self) -> CheckPluginName:
        if self.is_management_name():
            return CheckPluginName(self._value[len(self.MANAGEMENT_PREFIX) :])
        return self


class InventoryPluginName(ABCName):
    @classmethod
    def _legacy_naming_exceptions(cls) -> set[str]:
        return set()


class ServiceID(NamedTuple):
    name: CheckPluginName
    item: Item
