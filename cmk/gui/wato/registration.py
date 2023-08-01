#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0.base import PainterRegistry
from cmk.gui.plugins.wato import sync_remote_sites
from cmk.gui.views.icon import IconRegistry
from cmk.gui.views.sorter import SorterRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.wato.page_handler import page_handler
from cmk.gui.watolib.automation_commands import AutomationCommandRegistry
from cmk.gui.watolib.hosts_and_folders import ajax_popup_host_action_menu

from . import filters, pages
from .icons import DownloadAgentOutputIcon, DownloadSnmpWalkIcon, WatoIcon
from .mode import ModeRegistry
from .views import (
    PainterHostFilename,
    PainterWatoFolderAbs,
    PainterWatoFolderPlain,
    PainterWatoFolderRel,
    SorterWatoFolderAbs,
    SorterWatoFolderPlain,
    SorterWatoFolderRel,
)


def register(
    page_registry: PageRegistry,
    painter_registry: PainterRegistry,
    sorter_registry: SorterRegistry,
    icon_registry: IconRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
    filter_registry: FilterRegistry,
    mode_registry: ModeRegistry,
) -> None:
    painter_registry.register(PainterHostFilename)
    painter_registry.register(PainterWatoFolderAbs)
    painter_registry.register(PainterWatoFolderRel)
    painter_registry.register(PainterWatoFolderPlain)
    sorter_registry.register(SorterWatoFolderAbs)
    sorter_registry.register(SorterWatoFolderRel)
    sorter_registry.register(SorterWatoFolderPlain)

    icon_registry.register(DownloadAgentOutputIcon)
    icon_registry.register(DownloadSnmpWalkIcon)
    icon_registry.register(WatoIcon)

    page_registry.register_page_handler("wato", page_handler)
    page_registry.register_page_handler("ajax_popup_host_action_menu", ajax_popup_host_action_menu)

    sync_remote_sites.register(automation_command_registry, job_registry)
    filters.register(filter_registry)
    pages.register(page_registry, mode_registry)
