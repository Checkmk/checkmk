#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from logging import Logger

from livestatus import SiteId

from cmk.ccc.plugin_registry import Registry

from .logger import logger

RenameActionHandler = Callable[[SiteId, SiteId, Logger], None]


class RenameAction:
    """Base class for all site rename operations"""

    def __init__(
        self, name: str, title: str, sort_index: int, handler: RenameActionHandler
    ) -> None:
        self._name = name
        self._title = title
        self._sort_index = sort_index
        self._handler = handler

    @property
    def name(self) -> str:
        return self._name

    @property
    def title(self) -> str:
        return self._title

    @property
    def sort_index(self) -> int:
        return self._sort_index

    def run(self, old_site_id: SiteId, new_site_id: SiteId) -> None:
        """Execute the rename operation"""
        self._handler(old_site_id, new_site_id, logger)


class RenameActionRegistry(Registry[RenameAction]):
    def plugin_name(self, instance):
        return instance.name


rename_action_registry = RenameActionRegistry()
