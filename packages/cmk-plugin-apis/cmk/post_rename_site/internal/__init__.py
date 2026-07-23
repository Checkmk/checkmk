#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal post-rename-site API: the ``RenameAction`` plug-in type and its discovery prefix.

This is the ``internal`` variant of the per-domain post-rename-site API (see the
plugin discovery reference in ``cmk.discover_plugins``). It is not exposed to
third-party plug-in authors; it carries the actions ``cmk-post-rename-site``
runs after a site has been renamed.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from logging import Logger
from typing import Protocol


class Name(str): ...


class Title:
    def __init__(self, raw: str, /) -> None:
        self._raw = raw

    def localize(self, localizer: Callable[[str], str], /) -> str:
        return localizer(self._raw)


class SortIndex(int): ...


# Plugin-apis stays str-only; downstream specialises ``SiteIdT`` to
# ``cmk.ccc.site.SiteId`` to preserve strong typing without making
# plugin-apis depend on cmk-ccc.
class RenameActionHandler[SiteIdT: str](Protocol):
    def __call__(self, old_site_id: SiteIdT, new_site_id: SiteIdT, logger: Logger) -> None:
        pass


@dataclass(frozen=True, kw_only=True)
class RenameAction[SiteIdT: str]:
    """Plugin class for all site rename operations"""

    name: Name
    title: Title
    sort_index: SortIndex
    run: RenameActionHandler[SiteIdT]


def entry_point_prefixes() -> Mapping[type[RenameAction[str]], str]:
    return {RenameAction: "rename_action_"}


__all__ = [
    "Name",
    "RenameAction",
    "RenameActionHandler",
    "SortIndex",
    "Title",
    "entry_point_prefixes",
]
