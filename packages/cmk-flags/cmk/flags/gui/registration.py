#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.flags import gui as experimental_flags_gui
from cmk.flags.gui.global_config import (
    EXPERIMENTAL_FLAGS_CONFIG_DIR,
    EXPERIMENTAL_FLAGS_STAGED_FILENAME,
    is_development_site,
)
from cmk.gui.i18n import _
from cmk.gui.watolib.backup_snapshots import backup_domains
from cmk.gui_plugins.internal.feature_registration import GuiFeaturePlugin, RegistrationContext


def _register(ctx: RegistrationContext) -> None:
    experimental_flags_gui.register(
        ctx.config_domain_registry,
        ctx.config_variable_registry,
        ctx.config_variable_group_registry,
        show_in_global_settings=is_development_site(),
    )
    # Snapshots the staged flags, so that discarding changes reverts them.
    backup_domains["experimental_flags"] = {
        "group": _("Configuration"),
        "title": _("Experimental flags"),
        "prefix": EXPERIMENTAL_FLAGS_CONFIG_DIR,
        "paths": [("file", EXPERIMENTAL_FLAGS_STAGED_FILENAME)],
        "default": True,
    }


feature_plugin_experimental_flags = GuiFeaturePlugin(
    name="experimental_flags",
    register=_register,
)
