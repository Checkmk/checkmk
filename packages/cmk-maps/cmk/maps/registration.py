#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Composition root for Checkmk Maps.

Maps plugs itself into the GUI as a :class:`GuiFeaturePlugin` rather than being
called from each edition's ``registration.py``, so ``cmk.gui`` needs no import of
this package. ``cmk.gui.main_modules`` discovers this module by name and hands it
the registries it asks for.

This is the only place that sees both halves of the feature — the GUI
integration and the REST endpoints — which is why it lives next to them rather
than inside either (neither may import the other).
"""

from cmk.gui_plugins.internal.feature_registration import GuiFeaturePlugin, RegistrationContext
from cmk.maps import gui as maps_gui
from cmk.maps.rest_api import registration as maps_rest_api
from cmk.maps.rest_api.internal import registration as maps_rest_api_internal


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
    maps_rest_api.register(
        versioned_endpoint_registry=ctx.versioned_endpoint_registry,
        endpoint_family_registry=ctx.endpoint_family_registry,
    )
    maps_rest_api_internal.register(
        versioned_endpoint_registry=ctx.versioned_endpoint_registry,
        endpoint_family_registry=ctx.endpoint_family_registry,
    )


feature_plugin_maps = GuiFeaturePlugin(
    name="maps",
    register=_register,
)
