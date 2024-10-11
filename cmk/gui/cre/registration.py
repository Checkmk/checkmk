#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Raw edition and only raw edition specific registrations"""

from cmk.ccc.version import Edition

import cmk.gui.graphing._graph_images as graph_images
import cmk.gui.graphing._html_render as html_render
import cmk.gui.pages
from cmk.gui import hooks, sidebar, visuals
from cmk.gui.background_job import job_registry
from cmk.gui.backup.registration import backup_register
from cmk.gui.custom_icons.registration import custom_icons_register
from cmk.gui.dashboard import dashlet_registry
from cmk.gui.data_source import data_source_registry
from cmk.gui.features import Features, features_registry
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.metrics import PageGraphDashlet, PageHostServiceGraphPopup
from cmk.gui.mkeventd import registration as mkeventd_registration
from cmk.gui.mkeventd.helpers import save_active_config
from cmk.gui.openapi import endpoint_registry
from cmk.gui.pages import page_registry
from cmk.gui.painter.v0.base import painter_registry
from cmk.gui.permissions import permission_registry, permission_section_registry
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.sidebar import snapin_registry
from cmk.gui.sites import site_choices
from cmk.gui.valuespec import autocompleter_registry
from cmk.gui.views import graph
from cmk.gui.views.command import command_registry
from cmk.gui.views.icon import icon_and_action_registry
from cmk.gui.views.sorter import sorter_registry
from cmk.gui.visuals import default_site_filter_heading_info
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.wato import (
    default_user_menu_topics,
    notification_parameter_registry,
    NotificationParameterMail,
)
from cmk.gui.wato import registration as wato_registration
from cmk.gui.watolib.activate_changes import activation_features_registry, ActivationFeatures
from cmk.gui.watolib.analyze_configuration import ac_test_registry
from cmk.gui.watolib.automation_commands import automation_command_registry
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    sample_config_generator_registry,
)
from cmk.gui.watolib.config_sync import replication_path_registry
from cmk.gui.watolib.groups import contact_group_usage_finder_registry
from cmk.gui.watolib.main_menu import main_module_registry, main_module_topic_registry
from cmk.gui.watolib.mode import mode_registry
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry
from cmk.gui.watolib.search import match_item_generator_registry
from cmk.gui.watolib.timeperiods import timeperiod_usage_finder_registry


def register_pages() -> None:
    cmk.gui.pages.page_registry.register(PageGraphDashlet)
    cmk.gui.pages.page_registry.register(PageHostServiceGraphPopup)
    cmk.gui.pages.page_registry.register(html_render.AjaxRenderGraphContent)
    cmk.gui.pages.page_registry.register(html_render.AjaxGraphHover)
    cmk.gui.pages.page_registry.register(html_render.AjaxGraph)
    cmk.gui.pages.page_registry.register(graph_images.AjaxGraphImagesForNotifications)


def register_painters() -> None:
    painter_registry.register(graph.PainterServiceGraphs)
    painter_registry.register(graph.PainterHostGraphs)
    painter_registry.register(graph.PainterSvcPnpgraph)
    painter_registry.register(graph.PainterHostPnpgraph)


def register(edition: Edition) -> None:
    features_registry.register(
        Features(
            edition,
            livestatus_only_sites_postprocess=lambda x: list(x) if x else None,
        )
    )
    visuals.register(
        page_registry,
        visual_info_registry,
        filter_registry,
        autocompleter_registry,
        site_choices,
        default_site_filter_heading_info,
    )
    sidebar.register(
        page_registry,
        permission_section_registry,
        snapin_registry,
        dashlet_registry,
        mega_menu_registry,
        view_menu_topics=sidebar.default_view_menu_topics,
    )
    wato_registration.register(
        page_registry,
        painter_registry,
        sorter_registry,
        icon_and_action_registry,
        automation_command_registry,
        job_registry,
        filter_registry,
        mode_registry,
        quick_setup_registry,
        permission_section_registry,
        permission_registry,
        main_module_topic_registry,
        main_module_registry,
        rulespec_group_registry,
        config_domain_registry,
        config_variable_registry,
        config_variable_group_registry,
        snapin_registry,
        match_item_generator_registry,
        mega_menu_registry,
        ac_test_registry,
        contact_group_usage_finder_registry,
        notification_parameter_registry,
        replication_path_registry,
        default_user_menu_topics,
        edition_supports_ldap=True,
        edition_supports_managing_roles=True,
    )
    activation_features_registry.register(
        ActivationFeatures(
            edition,
            sync_file_filter_func=None,
        )
    )
    notification_parameter_registry.register(NotificationParameterMail)
    register_pages()
    register_painters()
    backup_register(
        page_registry,
        mode_registry,
        main_module_registry,
    )
    mkeventd_registration.register(
        permission_section_registry,
        permission_registry,
        data_source_registry,
        painter_registry,
        command_registry,
        sorter_registry,
        icon_and_action_registry,
        config_domain_registry,
        sample_config_generator_registry,
        mode_registry,
        main_module_registry,
        config_variable_group_registry,
        config_variable_registry,
        rulespec_group_registry,
        rulespec_registry,
        autocompleter_registry,
        filter_registry,
        notification_parameter_registry,
        snapin_registry,
        contact_group_usage_finder_registry,
        timeperiod_usage_finder_registry,
        endpoint_registry,
        replication_path_registry,
    )
    hooks.register_builtin("mkeventd-activate-changes", save_active_config)
    custom_icons_register(
        mode_registry,
        main_module_registry,
        permission_registry,
    )
