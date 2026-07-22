#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The context the backend provides to a plugin handler at collect time"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


# TODO: see if we can use Logger or omit it entirely (plugins can use logging.getLogger)
class CollectLogger(Protocol):
    """Log messages that end up in the dump's console log"""

    def info(self, message: str) -> None: ...

    def warning(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...


# TODO: this needs to be simplied.
@dataclass(frozen=True, kw_only=True)
class CollectContext:
    """Capabilities and site facts the backend provides at collect time"""

    omd_root: Path
    omd_config: Mapping[str, str]
    all_parameters: Mapping[str, object]
    """The complete resolved dump parameters (for the 'parameters' plugin)"""
    core_performance_settings: Mapping[str, int]
    """Edition specific performance settings of the monitoring core"""
    resolve_checkmk_server_host: Callable[[], str]
    """Return the host monitoring the Checkmk server; may raise :class:`CollectWarning`"""
    site_internal_auth_header: Callable[[], str]
    """Authorization header value for HTTP requests against the own site"""
    log: CollectLogger
