#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, Never, NotRequired, Protocol, TypedDict

from cmk.agent_based.v2 import CheckPlugin

# Watch out! Matching the 'logwatch_rules' ruleset against labels will not
# work as expected, if logfiles are grouped!
NEVER_DISCOVER_SERVICE_LABELS: Sequence[Never] = ()


SyslogConfig = tuple[Literal["tcp"], dict] | tuple[Literal["udp"], dict]  # type: ignore[type-arg]


class CommonLogwatchEc(TypedDict):
    activation: NotRequired[bool]
    method: NotRequired[Literal["", "spool:"] | str | SyslogConfig]
    facility: NotRequired[int]
    restrict_logfiles: NotRequired[list[str]]
    monitor_logfilelist: NotRequired[bool]
    expected_logfiles: NotRequired[list[str]]
    logwatch_reclassify: NotRequired[bool]
    monitor_logfile_access_state: NotRequired[Literal[0, 1, 2, 3]]
    separate_checks: NotRequired[bool]


class ParameterLogwatchEc(CommonLogwatchEc):
    """Parameters as created by the 'logwatch_ec' ruleset"""

    service_level: int
    host_name: str
    is_preview: bool


StateMap = Mapping[Literal["c_to", "w_to", "o_to", "._to"], Literal["C", "W", "O", "I", "."]]


class ParameterLogwatchRules(TypedDict):
    reclassify_patterns: list[tuple[Literal["C", "W", "O", "I"], str, str]]
    reclassify_states: NotRequired[StateMap]


class LogwatchConfigP(Protocol):
    @property
    def msg_dir(self) -> Path: ...

    @property
    def base_spool_path(self) -> Path: ...

    @property
    def omd_root(self) -> Path: ...

    @property
    def debug(self) -> bool: ...

    def logwatch_rules_all(
        self, *, host_name: str, plugin: CheckPlugin, logfile: str
    ) -> Sequence[ParameterLogwatchRules]: ...

    def logwatch_ec_all(self, host_name: str) -> Sequence[ParameterLogwatchEc]: ...


# This is obviously bad practice.
# But I rather have an isolated global state here then in cmk.base.config :-/
_g_state_config: LogwatchConfigP | None = None


def set_global_state(config: LogwatchConfigP) -> None:
    global _g_state_config
    _g_state_config = config


def unset_global_state() -> None:
    """Reset the global state. Only used in tests."""
    global _g_state_config
    _g_state_config = None


def get_global_state() -> LogwatchConfigP:
    if _g_state_config is None:
        raise RuntimeError("global state not initialised")
    return _g_state_config
