#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Recipes for the files a core bakelet deploys.

These types are data only. The bakery turns them into its file containers,
so a bakelet handles neither placement nor permissions nor the source lookup.
Use the artifact types of :mod:`cmk.bakery.v2_unstable` where they suffice and
these types for what the versioned API cannot express.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.bakery.v2 import OS

from ._constants import LogicalPath


@dataclass(frozen=True, kw_only=True)
class PluginExecution:
    """How the agent runs a plug-in. Valid with ``location=LogicalPath.PLUGINS`` only."""

    interval: int | None = None
    asynchronous: bool | None = None
    timeout: int | None = None
    retry_count: int | None = None


@dataclass(frozen=True, kw_only=True)
class SiteFile:
    """A file copied from the Checkmk site.

    ``source`` is looked up in the agents folder of the bakelet's plug-in family
    first and in the site's agents directories second. Every source line that
    starts with a key of ``line_mapping`` is replaced by that key's value.
    """

    base_os: OS
    source: Path
    location: LogicalPath
    target: Path | None = None
    line_mapping: Mapping[str, str] | None = None
    execution: PluginExecution | None = None

    def __post_init__(self) -> None:
        if not self.line_mapping:
            object.__setattr__(self, "line_mapping", None)


@dataclass(frozen=True, kw_only=True)
class TextFile:
    """A file written from ``lines``. ``include_header`` prepends the bakery header."""

    base_os: OS
    lines: Sequence[str]
    target: Path
    location: LogicalPath
    include_header: bool = False
    execution: PluginExecution | None = None


@dataclass(frozen=True, kw_only=True)
class BinaryFile:
    base_os: OS
    content: bytes
    target: Path
    location: LogicalPath


@dataclass(frozen=True, kw_only=True)
class CustomFile:
    """A user-provided file from ``custom/<package>/<subdir>`` in the site's agents
    directory, with the subdir taken from ``CUSTOM_FILE_SUBDIRS[location]``."""

    base_os: OS
    source: Path
    package: str
    location: LogicalPath


@dataclass(frozen=True, kw_only=True)
class HashDependency:
    """A file that deploys nothing but whose stat enters the agent hash.

    A change to the file then forces a rebake, for content the bakelet reads
    itself and hands over as generated content.
    """

    path: Path
