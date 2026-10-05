#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Base classes and registry for automation results.

Provides the abstract result type, the serialization wrapper, and the global
registry that all concrete result modules register into.
"""

from abc import ABC, abstractmethod
from ast import literal_eval
from dataclasses import astuple, dataclass
from typing import override, Self

from cmk.ccc.plugin_registry import Registry
from cmk.ruleset_matcher.labels import HostLabelValueDict

from ..types import AutomationID

DiscoveredHostLabelsDict = dict[str, HostLabelValueDict]


class ResultTypeRegistry(Registry[type["AutomationResult"]]):
    @override
    def plugin_name(self, instance: type[AutomationResult]) -> AutomationID:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()


@dataclass
class AutomationResult(ABC):
    def serialize(self, _for_cmk_version: str, /) -> str:
        """Serialize the result for a peer running the given Checkmk version.

        The version lets a result stay compatible with older central sites. Results
        that depend on it may parse it with ``cmk.ccc.version.Version.from_str``.
        """
        return self._default_serialize()

    @classmethod
    def deserialize(cls, serialized_result: str, /) -> Self:
        return cls(*literal_eval(serialized_result))

    @staticmethod
    @abstractmethod
    def automation_call() -> AutomationID: ...

    def _default_serialize(self) -> str:
        return repr(astuple(self))
