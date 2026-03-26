#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Base classes and registry for automation results.

Provides the abstract result type, the serialization wrapper, and the global
registry that all concrete result modules register into.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from ast import literal_eval
from dataclasses import astuple, dataclass
from typing import TypeVar

from cmk.ccc import version as cmk_version
from cmk.ccc.plugin_registry import Registry
from cmk.utils.labels import HostLabelValueDict

from ..types import AutomationID

DiscoveredHostLabelsDict = dict[str, HostLabelValueDict]


class ResultTypeRegistry(Registry[type["ABCAutomationResult"]]):
    def plugin_name(self, instance: type[ABCAutomationResult]) -> AutomationID:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()


class SerializedResult(str): ...


_DeserializedType = TypeVar("_DeserializedType", bound="ABCAutomationResult")


@dataclass
class ABCAutomationResult(ABC):
    def serialize(
        self,
        for_cmk_version: cmk_version.Version,  # used to stay compatible with older central sites
    ) -> SerializedResult:
        return self._default_serialize()

    @classmethod
    def deserialize(
        cls: type[_DeserializedType],
        serialized_result: SerializedResult,
    ) -> _DeserializedType:
        return cls(*literal_eval(serialized_result))

    @staticmethod
    @abstractmethod
    def automation_call() -> AutomationID: ...

    def _default_serialize(self) -> SerializedResult:
        return SerializedResult(repr(astuple(self)))
