#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0.base import PainterRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.views.sorter import SorterRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.wato.page_handler import page_handler
from cmk.gui.watolib.automation_commands import AutomationCommandRegistry
from cmk.gui.watolib.hosts_and_folders import ajax_popup_host_action_menu
from cmk.gui.watolib.main_menu import MainModuleRegistry, MainModuleTopicRegistry
from cmk.gui.watolib.mode import ModeRegistry

from . import _main_module_topics, _main_modules, _permissions, _pre_21_plugin_api, filters, pages
from .icons import DownloadAgentOutputIcon, DownloadSnmpWalkIcon, WatoIcon
from .pages._rule_conditions import PageAjaxDictHostTagConditionGetChoice
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
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    main_module_topic_registry: MainModuleTopicRegistry,
    main_module_registry: MainModuleRegistry,
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
    page_registry.register_page("ajax_dict_host_tag_condition_get_choice")(
        PageAjaxDictHostTagConditionGetChoice
    )

    filters.register(filter_registry)
    pages.register(page_registry, mode_registry)
    _permissions.register(permission_section_registry, permission_registry)
    _main_module_topics.register(main_module_topic_registry)
    _main_modules.register(main_module_registry)
    _pre_21_plugin_api.register()
