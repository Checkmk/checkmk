#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.painter_options import PainterOptionRegistry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.sidebar import SnapinRegistry
from cmk.gui.views.command import CommandGroupRegistry, CommandRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.watolib.host_rename import RenameHostHook, RenameHostHookRegistry, RenamePhase
from cmk.gui.watolib.main_menu import MainModuleRegistry, MainModuleTopicRegistry
from cmk.gui.watolib.mode import ModeRegistry

from . import _config, _filters, _icons, _openapi, _snapins, _valuespecs
from ._host_rename import rename_host_in_bi
from .ajax_endpoints import ajax_render_tree, ajax_save_treestate, ajax_set_assumption
from .permissions import PERMISSION_SECTION_BI, PermissionBISeeAll
from .view import (
    CommandFreezeAggregation,
    CommandGroupAggregations,
    DataSourceBIAggregations,
    DataSourceBIHostAggregations,
    DataSourceBIHostnameAggregations,
    DataSourceBIHostnameByGroupAggregations,
    PainterAggrAcknowledged,
    PainterAggrAssumedState,
    PainterAggrGroup,
    PainterAggrHosts,
    PainterAggrHostsServices,
    PainterAggrIcons,
    PainterAggrInDowntime,
    PainterAggrName,
    PainterAggrOutput,
    PainterAggrRealState,
    PainterAggrState,
    PainterAggrStateNum,
    PainterAggrTreestate,
    PainterAggrTreestateBoxed,
    PainterAggrTreestateFrozenDiff,
    PainterOptionAggrExpand,
    PainterOptionAggrOnlyProblems,
    PainterOptionAggrTreeType,
    PainterOptionAggrWrap,
)


def register(
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    painter_option_registry: PainterOptionRegistry,
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    page_registry: PageRegistry,
    filter_registry: FilterRegistry,
    rename_host_hook_registry: RenameHostHookRegistry,
    main_module_topic_registry: MainModuleTopicRegistry,
    main_module_registry: MainModuleRegistry,
    mode_registry: ModeRegistry,
    icon_and_action_registry: IconRegistry,
    snapin_registry: SnapinRegistry,
    endpoint_registry: EndpointRegistry,
    command_registry: CommandRegistry,
    command_group_registry: CommandGroupRegistry,
    *,
    ignore_duplicate_endpoints: bool = False,
) -> None:
    data_source_registry.register(DataSourceBIAggregations)
    data_source_registry.register(DataSourceBIHostAggregations)
    data_source_registry.register(DataSourceBIHostnameAggregations)
    data_source_registry.register(DataSourceBIHostnameByGroupAggregations)

    painter_registry.register(PainterAggrIcons)
    painter_registry.register(PainterAggrInDowntime)
    painter_registry.register(PainterAggrAcknowledged)
    painter_registry.register(PainterAggrState)
    painter_registry.register(PainterAggrStateNum)
    painter_registry.register(PainterAggrRealState)
    painter_registry.register(PainterAggrAssumedState)
    painter_registry.register(PainterAggrGroup)
    painter_registry.register(PainterAggrName)
    painter_registry.register(PainterAggrOutput)
    painter_registry.register(PainterAggrHosts)
    painter_registry.register(PainterAggrHostsServices)
    painter_registry.register(PainterAggrTreestate)
    painter_registry.register(PainterAggrTreestateFrozenDiff)
    painter_registry.register(PainterAggrTreestateBoxed)

    painter_option_registry.register(PainterOptionAggrExpand())
    painter_option_registry.register(PainterOptionAggrOnlyProblems())
    painter_option_registry.register(PainterOptionAggrTreeType())
    painter_option_registry.register(PainterOptionAggrWrap())

    permission_section_registry.register(PERMISSION_SECTION_BI)
    permission_registry.register(PermissionBISeeAll)

    command_group_registry.register(CommandGroupAggregations)
    command_registry.register(CommandFreezeAggregation)

    page_registry.register(PageEndpoint("bi_set_assumption", ajax_set_assumption))
    page_registry.register(PageEndpoint("bi_save_treestate", ajax_save_treestate))
    page_registry.register(PageEndpoint("bi_render_tree", ajax_render_tree))

    _filters.register(filter_registry)
    _config.register(
        page_registry,
        main_module_topic_registry,
        main_module_registry,
        mode_registry,
        permission_registry,
    )
    _icons.register(icon_and_action_registry)
    _snapins.register(snapin_registry)
    _valuespecs.register()

    rename_host_hook_registry.register(
        RenameHostHook(RenamePhase.SETUP, "BI aggregations", rename_host_in_bi)
    )
    _openapi.register(endpoint_registry, ignore_duplicates=ignore_duplicate_endpoints)
