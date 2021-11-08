#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Final, Optional

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostLabelValueDict, SectionName


class _Label:
    """Representing a label in Checkmk"""

    __slots__ = "name", "value"

    def __init__(self, name: str, value: str) -> None:

        if not isinstance(name, str):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self.name: Final = str(name)

        if not isinstance(value, str):
            raise MKGeneralException("Invalid label value given: Only unicode strings are allowed")
        self.value: Final = str(value)

    @property
    def label(self) -> str:
        return f"{self.name}:{self.value}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r}, {self.value!r})"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" % (type(self), type(other)))
        return self.name == other.name and self.value == other.value


class ServiceLabel(_Label):
    __slots__ = ()


class HostLabel(_Label):
    """Representing a host label in Checkmk during runtime

    Besides the label itself it keeps the information which plugin discovered the host label
    """

    __slots__ = ("plugin_name",)

    @classmethod
    def from_dict(cls, name: str, dict_label: HostLabelValueDict) -> "HostLabel":
        value = dict_label["value"]
        assert isinstance(value, str)

        raw_name = dict_label["plugin_name"]
        plugin_name = None if raw_name is None else SectionName(raw_name)

        return cls(name, value, plugin_name)

    def __init__(
        self,
        name: str,
        value: str,
        plugin_name: Optional[SectionName] = None,
    ) -> None:
        super().__init__(name, value)
        self.plugin_name: Final = plugin_name

    def to_dict(self) -> HostLabelValueDict:
        return {
            "value": self.value,
            "plugin_name": None if self.plugin_name is None else str(self.plugin_name),
        }

    def __repr__(self) -> str:
        return f"HostLabel({self.name!r}, {self.value!r}, plugin_name={self.plugin_name!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HostLabel):
            raise TypeError(f"{other!r} is not of type HostLabel")
        return (
            self.name == other.name
            and self.value == other.value
            and self.plugin_name == other.plugin_name
        )

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
