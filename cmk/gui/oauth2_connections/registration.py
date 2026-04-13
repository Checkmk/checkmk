#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.form_specs.visitors import register_recomposer_function, register_visitor_class
from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import PermissionRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry
from cmk.rulesets.internal.form_specs import OAuth2Connection

from .permissions import PermissionUseOAuthConnections
from .recomposer import recompose as recompose_oauth2_connection
from .visitor import OAuth2ConnectionSetupVisitor
from .wato import register_main_module, register_modes, register_pages


def register(
    mode_registry: ModeRegistry,
    page_registry: PageRegistry,
    main_module_registry: MainModuleRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    register_modes(mode_registry)
    register_pages(page_registry)
    register_main_module(main_module_registry)
    permission_registry.register(PermissionUseOAuthConnections)
    register_visitor_class(OAuth2ConnectionSetup, OAuth2ConnectionSetupVisitor)
    register_recomposer_function(OAuth2Connection, recompose_oauth2_connection)
