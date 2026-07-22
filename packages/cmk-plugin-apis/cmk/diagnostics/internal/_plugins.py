#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The plug-in type of the support diagnostics domain

A support diagnostics dump is a tarball of files collected on a site. Each
plug-in contributes files via its handler; the backend engine is a pure
packer. All reading, generating, filtering and transformation is done by the
plug-in itself.
"""

import enum
import functools
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ._context import CollectContext
from ._localize import Help, Topic


@functools.total_ordering
class Sensitivity(enum.Enum):
    """How sensitive the data collected by a plug-in is

    LOW: no sensitive data at all.
    MEDIUM: may include IP addresses, host names, usernames, mail addresses.
    HIGH: may include highly sensitive data like passwords.

    A plug-in must only bundle files of its declared sensitivity in one
    handler; users select a sensitivity threshold per topic.
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Sensitivity):
            return NotImplemented
        return self.value < other.value


@dataclass(frozen=True)
class GeneratedContent:
    """Content produced by the plug-in itself"""

    data: bytes


@dataclass(frozen=True)
class VerbatimCopy:
    """An existing file, streamed into the dump untouched

    The engine never transforms a verbatim copy. A plug-in that needs
    sanitization or redaction must produce :class:`GeneratedContent` instead.
    """

    source: Path


DumpItem = tuple[PurePosixPath, GeneratedContent | VerbatimCopy]
"""One file of the dump: the relative path inside the dump archive and its content"""


@dataclass(frozen=True, kw_only=True)
class DiagnosticsPlugin:
    """A support diagnostics plug-in

    The handler yields the files this plug-in contributes to the dump. It may
    raise :class:`CollectInfo`, :class:`CollectWarning` or
    :class:`CollectError` to report on the collection; files yielded before
    raising remain part of the dump.
    """

    name: str
    description: Help
    """Short human friendly description, shown in the GUI"""
    sensitivity: Sensitivity
    topic: Topic
    always: bool = False
    """Collected in every dump; not deselectable"""
    needs_checkmk_server_host: bool = False
    """Whether the handler reads :meth:`CollectContext.resolve_checkmk_server_host`"""
    handler: Callable[[CollectContext], Iterable[DumpItem]]
