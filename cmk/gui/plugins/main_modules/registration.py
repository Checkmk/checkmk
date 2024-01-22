#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Central module for common (non-edition specific) registrations"""


from functools import partial

from cmk.utils.licensing.registry import register_cre_licensing_handler

import cmk.gui.pages
from cmk.gui import autocompleters, crash_reporting, dashboard, hooks, mobile, views, visuals, wato
from cmk.gui.bi import registration as bi_registration
from cmk.gui.config import register_post_config_load_hook
from cmk.gui.dashboard import dashlet_registry
from cmk.gui.mkeventd import registration as mkeventd_registration
from cmk.gui.mkeventd.helpers import save_active_config
from cmk.gui.permissions import permission_registry, permission_section_registry
from cmk.gui.plugins.visuals import filters
from cmk.gui.plugins.visuals.utils import visual_type_registry
from cmk.gui.plugins.wato.utils import mode_registry
from cmk.gui.plugins.watolib.utils import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    sample_config_generator_registry,
)
from cmk.gui.query_filters import cre_sites_options
from cmk.gui.valuespec import autocompleter_registry
from cmk.gui.views.command import command_registry
from cmk.gui.views.data_source import data_source_registry
from cmk.gui.views.icon import icon_and_action_registry
from cmk.gui.views.inventory.row_post_processor import inventory_row_post_processor
from cmk.gui.views.join_service_rows import join_service_row_post_processor
from cmk.gui.views.layout import layout_registry
from cmk.gui.views.painter.v0.base import painter_registry
from cmk.gui.views.painter_options import painter_option_registry
from cmk.gui.views.row_post_processing import register_row_post_processor
from cmk.gui.views.sorter import sorter_registry
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry


def register_sites_options() -> None:
    hooks.register_builtin("mkeventd-activate-changes", save_active_config)
    filters.MultipleSitesFilter.sites_options = cre_sites_options
    autocompleter_registry.register_expression("sites")(
        partial(autocompleters.sites_autocompleter, sites_options=cre_sites_options)
    )


def register() -> None:
    register_cre_licensing_handler()
    visuals.register(cmk.gui.pages.page_registry)
    views.register(
        permission_section_registry,
        cmk.gui.pages.page_registry,
        visual_type_registry,
        register_post_config_load_hook,
    )
    dashboard.register(
        permission_section_registry,
        cmk.gui.pages.page_registry,
        visual_type_registry,
        dashlet_registry,
    )
    crash_reporting.register(
        cmk.gui.pages.page_registry,
        data_source_registry,
        painter_registry,
        sorter_registry,
        command_registry,
    )
    mkeventd_registration.register(
        permission_section_registry,
        permission_registry,
        data_source_registry,
        painter_registry,
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
    )
    mobile.register(layout_registry)
    wato.register(painter_registry, sorter_registry, icon_and_action_registry)
    bi_registration.register(
        data_source_registry,
        painter_registry,
        painter_option_registry,
        permission_section_registry,
        permission_registry,
        cmk.gui.pages.page_registry,
    )
    register_sites_options()
    register_row_post_processor(inventory_row_post_processor)
    register_row_post_processor(join_service_row_post_processor)


register()
