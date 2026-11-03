#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What the monitoring pages and endpoints need from Setup's folders.

Setup satisfies these protocols structurally and is injected at wiring time, so neither side
imports the other.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Protocol

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.tags import TagConfig

__all__ = ["SetupFolders", "SetupFoldersConfig", "SetupFolderSource"]


class SetupFolders(Protocol):
    """What this domain needs from Setup: how its folders are titled, and who may open a host.

    Two questions about titles rather than one mapping, because they do not cost the same: the
    title of one folder is a lookup, while every title means walking the whole folder tree - which
    the column, redrawn on a timer, has no business doing. Setup answers them off the folder tree
    it read for the request.

    Whether the user may open a host in Setup decides whether a page links there at all: Setup
    restricts its hosts by contact group, so a user allowed into Setup may still be refused the one
    host a row shows. The folder path, when known, spares Setup the search for the host.
    """

    def title_of(self, path: str) -> str | None: ...

    def all_titles(self) -> Mapping[str, str]: ...

    def may_read_host(self, host_name: str, path: str | None) -> bool: ...


class SetupFoldersConfig(Protocol):
    """The part of a request's config Setup reads its folder tree from.

    Satisfied by the GUI's Config as well as by the REST API's ApiConfig.
    """

    @property
    def wato_hide_folders_without_read_permissions(self) -> bool: ...

    @property
    def wato_host_attrs(self) -> Sequence[CustomHostAttrSpec]: ...

    @property
    def tags(self) -> TagConfig: ...

    @property
    def sites(self) -> SiteConfigurations: ...


type SetupFolderSource = Callable[[SetupFoldersConfig, LoggedInUser], SetupFolders]
"""How a page or an endpoint gets Setup's folders: read from the request's config, for its user."""
