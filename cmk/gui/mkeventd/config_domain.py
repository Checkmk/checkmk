#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.site import omd_site

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui import hooks
from cmk.gui.config import active_config
from cmk.gui.plugins.watolib.utils import ABCConfigDomain, SerializedSettings
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib import config_domain_name
from cmk.gui.watolib.audit_log import log_audit

from .livestatus import execute_command


class ConfigDomainEventConsole(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    in_global_settings = False

    @classmethod
    def ident(cls) -> config_domain_name.ConfigDomainName:
        return config_domain_name.EVENT_CONSOLE

    @classmethod
    def enabled(cls):
        return active_config.mkeventd_enabled

    def config_dir(self):
        return str(ec.rule_pack_dir())

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        if getattr(active_config, "mkeventd_enabled", False):
            execute_command("RELOAD", site=omd_site())
            log_audit("mkeventd-activate", "Activated changes of event console configuration")
            if hooks.registered("mkeventd-activate-changes"):
                hooks.call("mkeventd-activate-changes")
        return []

    def default_globals(self) -> GlobalSettings:
        return ec.default_config()
