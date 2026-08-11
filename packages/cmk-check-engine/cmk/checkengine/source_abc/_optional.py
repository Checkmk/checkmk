#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Sized
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.filecache import MaxAge
from cmk.ruleset_matcher.tags import ComputedDataSources

from ._abc import Source


@dataclass(frozen=True)
class SourceContext:
    """The host's source configuration, handed to discoverable optional sources.

    This bundles the ``SourceBuilder`` inputs an *additive* source may need to decide
    whether it applies and how to build itself. It is intentionally a superset that may
    grow as further optional sources are added.
    """

    host_name: HostName
    ipaddress: HostAddress | None
    computed_datasources: ComputedDataSources
    max_age_agent: MaxAge
    file_cache_path_base: Path
    file_cache_path_relative: Path
    omd_root: Path
    metrics_association: str | None
    check_mk_check_interval: float


class OptionalSource[TRawData: Sized](Source[TRawData], abc.ABC):
    """A `Source` that discovers and builds itself from a `SourceContext`.

    Sources subclassing this are found by `discover()` over the `cmk.checkengine.sources`
    namespace package, so an edition-gated source drops in or out purely by being shipped
    (or not) -- no by-name reference is needed in `SourceBuilder`. Each such source keeps
    the knowledge of *whether it applies* and *how to construct itself* in
    `from_context`, rather than in the builder.
    """

    @classmethod
    @abc.abstractmethod
    def from_context(cls, ctx: SourceContext) -> Self | None:
        """Build the source for this host, or return `None` if it does not apply."""
