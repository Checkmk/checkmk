#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Central module for common (non-edition specific) registrations"""


from functools import partial

import cmk.gui.pages
from cmk.gui import autocompleters, bi, crash_reporting, mkeventd, mobile, views, wato
from cmk.gui.config import register_post_config_load_hook
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
from cmk.gui.views import icon, inventory, perfometer
from cmk.gui.views.command import (
    command_group_registry,
    command_registry,
    register_command_groups,
    register_commands,
)
from cmk.gui.views.data_source import data_source_registry, register_data_sources
from cmk.gui.views.host_tag_plugins import register_tag_plugins
from cmk.gui.views.icon import icon_and_action_registry
from cmk.gui.views.layout import layout_registry, register_layouts
from cmk.gui.views.painter.v0 import painters
from cmk.gui.views.painter.v0.base import painter_registry
from cmk.gui.views.painter_options import painter_option_registry
from cmk.gui.views.sorter import register_sorters, sorter_registry
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry


def register_sites_options() -> None:
    filters.MultipleSitesFilter.sites_options = cre_sites_options

    autocompleter_registry.register_expression("sites")(
        partial(autocompleters.sites_autocompleter, sites_options=cre_sites_options)
    )


views.register(permission_section_registry, cmk.gui.pages.page_registry, visual_type_registry)

crash_reporting.register(
    cmk.gui.pages.page_registry,
    data_source_registry,
    painter_registry,
    sorter_registry,
    command_registry,
)
register_post_config_load_hook(register_tag_plugins)
register_layouts(layout_registry)
painters.register(painter_option_registry, painter_registry)
register_sorters(sorter_registry)
register_command_groups(command_group_registry)
register_commands(command_registry)
register_data_sources(data_source_registry)
perfometer.register(sorter_registry, painter_registry)
icon.register(icon.icon_and_action_registry, painter_registry, permission_section_registry)
mkeventd.register(
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
)
mobile.register(layout_registry)
wato.register(painter_registry, sorter_registry, icon_and_action_registry)
inventory.register()
bi.register(
    permission_section_registry,
    permission_registry,
    data_source_registry,
    painter_registry,
    painter_option_registry,
)
register_sites_options()
