#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Composition root for Checkmk Maps.

Maps plugs itself into the GUI as a :class:`GuiFeaturePlugin` rather than being
called from each edition's ``registration.py``, so ``cmk.gui`` needs no import of
this package. ``cmk.gui.main_modules`` discovers this module by name and hands it
the registries it asks for.

It sits beside the feature's parts rather than inside one of them, so no part
has to import another.
"""

from cmk.gui_plugins.internal.feature_registration import GuiFeaturePlugin, RegistrationContext
from cmk.maps import gui as maps_gui


def _register(ctx: RegistrationContext) -> None:
    maps_gui.register(
        ctx.permission_section_registry,
        ctx.permission_registry,
        ctx.page_registry,
        ctx.config_domain_registry,
        ctx.config_variable_group_registry,
        ctx.config_variable_registry,
        ctx.replication_path_registry,
        ctx.sample_config_generator_registry,
        ctx.mode_registry,
    )


feature_plugin_maps = GuiFeaturePlugin(
    name="maps",
    register=_register,
)
