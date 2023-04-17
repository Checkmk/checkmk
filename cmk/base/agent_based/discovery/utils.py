#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from collections.abc import Callable, Hashable, Iterable, Sequence
from typing import Final, Generic, Literal, TypeVar

from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.type_defs import HostName, RuleSetName

from cmk.checkers import Parameters

from cmk.base.api.agent_based.type_defs import ParametersTypeAlias
from cmk.base.config import ConfigCache


class DiscoveryMode(enum.Enum):
    # NOTE: the values 0-3 are used in WATO rules and must not be changed!
    NEW = 0
    REMOVE = 1
    FIXALL = 2
    REFRESH = 3
    ONLY_HOST_LABELS = 4
    FALLBACK = 5  # not sure why this could happen

    @classmethod
    def _missing_(cls, value: object) -> "DiscoveryMode":
        return cls.FALLBACK

    @classmethod
    def from_str(cls, value: str) -> "DiscoveryMode":
        # NOTE: 'only-host-labels' is sent by an automation call, so we need to deal with that.
        return cls[value.upper().replace("-", "_")]


_DiscoveredItem = TypeVar("_DiscoveredItem")


class QualifiedDiscovery(Generic[_DiscoveredItem]):
    """Classify items into "new", "old" and "vanished" ones."""

    def __init__(
        self,
        *,
        preexisting: Sequence[_DiscoveredItem],
        current: Sequence[_DiscoveredItem],
        key: Callable[[_DiscoveredItem], Hashable],
    ) -> None:
        current_dict = {key(v): v for v in current}
        preexisting_dict = {key(v): v for v in preexisting}

        self.vanished: Final = [v for k, v in preexisting_dict.items() if k not in current_dict]
        self.old: Final = [v for k, v in preexisting_dict.items() if k in current_dict]
        self.new: Final = [v for k, v in current_dict.items() if k not in preexisting_dict]
        self.present: Final = self.old + self.new

    @classmethod
    def empty(cls) -> "QualifiedDiscovery":
        """create an empty instance"""
        return cls(preexisting=(), current=(), key=repr)

    def chain_with_qualifier(
        self,
    ) -> Iterable[tuple[Literal["vanished", "old", "new"], _DiscoveredItem]]:
        for i in self.vanished:
            yield "vanished", i
        for i in self.old:
            yield "old", i
        for i in self.new:
            yield "new", i


def get_plugin_parameters(
    host_name: HostName,
    config_cache: ConfigCache,
    *,
    default_parameters: ParametersTypeAlias | None,
    ruleset_name: RuleSetName | None,
    ruleset_type: Literal["all", "merged"],
    rules_getter_function: Callable[[RuleSetName], Sequence[RuleSpec]],
) -> None | Parameters | list[Parameters]:
    if default_parameters is None:
        # This means the function will not accept any params.
        return None
    if ruleset_name is None:
        # This means we have default params, but no rule set.
        # Not very sensical for discovery functions, but not forbidden by the API either.
        return Parameters(default_parameters)

    rules = rules_getter_function(ruleset_name)

    if ruleset_type == "all":
        host_rules = config_cache.host_extra_conf(host_name, rules)
        host_rules.append(default_parameters)
        return [Parameters(d) for d in host_rules]

    if ruleset_type == "merged":
        return Parameters(
            {
                **default_parameters,
                **config_cache.host_extra_conf_merged(host_name, rules),
            }
        )

    # validation should have prevented this
    raise NotImplementedError(f"unknown discovery rule set type {ruleset_type!r}")
