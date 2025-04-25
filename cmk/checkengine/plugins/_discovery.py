#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import NamedTuple, TypedDict

from cmk.ccc.hostaddress import HostName

from cmk.utils.servicename import Item

from cmk.checkengine.parameters import Parameters
from cmk.checkengine.sectionparser import ParsedSectionName

from ._check import CheckPluginName, ServiceID


class _AutocheckDict(TypedDict):
    check_plugin_name: str
    item: str | None
    parameters: Mapping[str, object]
    service_labels: Mapping[str, str]


class AutocheckEntry(NamedTuple):
    check_plugin_name: CheckPluginName
    item: Item
    parameters: Mapping[str, object]
    service_labels: Mapping[str, str]

    @staticmethod
    def _parse_parameters(parameters: object) -> Mapping[str, object]:
        if isinstance(parameters, dict):
            return {str(k): v for k, v in parameters.items()}

        raise ValueError(f"Invalid autocheck: invalid parameters: {parameters!r}")

    @staticmethod
    def _parse_labels(labels: object) -> Mapping[str, str]:
        if isinstance(labels, dict):
            return {str(k): str(v) for k, v in labels.items()}

        raise ValueError(f"Invalid autocheck: invalid labels: {labels!r}")

    @classmethod
    def load(cls, raw_dict: Mapping[str, object]) -> AutocheckEntry:
        return cls(
            check_plugin_name=CheckPluginName(str(raw_dict["check_plugin_name"])),
            item=None if (raw_item := raw_dict["item"]) is None else str(raw_item),
            parameters=cls._parse_parameters(raw_dict["parameters"]),
            service_labels=cls._parse_labels(raw_dict["service_labels"]),
        )

    def id(self) -> ServiceID:
        """The identity of the service.

        As long as this does not change, we're talking about "the same" service (but it might have changed).
        """
        return ServiceID(self.check_plugin_name, self.item)

    def comparator(self) -> tuple[Mapping[str, object], Mapping[str, str]]:
        return self.parameters, self.service_labels

    def dump(self) -> _AutocheckDict:
        return {
            "check_plugin_name": str(self.check_plugin_name),
            "item": self.item,
            "parameters": self.parameters,
            "service_labels": self.service_labels,
        }


@dataclass(frozen=True)
class DiscoveryPlugin:
    sections: Sequence[ParsedSectionName]
    function: Callable[..., Iterable[AutocheckEntry]]
    parameters: Callable[[HostName], Sequence[Parameters] | Parameters | None]
