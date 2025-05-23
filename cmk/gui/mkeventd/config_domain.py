#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path
from typing import Final, override

from cmk.ccc.site import omd_site

from cmk.utils.config_warnings import ConfigurationWarnings

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, ConfigDomainName, SerializedSettings

from .livestatus import execute_command

EVENT_CONSOLE: Final[ConfigDomainName] = "ec"


class ConfigDomainEventConsole(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    in_global_settings = False

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return EVENT_CONSOLE

    @override
    @classmethod
    def enabled(cls) -> bool:
        return active_config.mkeventd_enabled

    def __init__(self, save_active_config: Callable[[], None]):
        super().__init__()
        self._save_active_config = save_active_config

    @override
    def config_dir(self) -> Path:
        return ec.rule_pack_dir()

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        if getattr(active_config, "mkeventd_enabled", False):
            log_audit(
                action="mkeventd-activate",
                message="Activated changes of event console configuration",
                user_id=user.id,
                use_git=active_config.wato_use_git,
            )
            self._save_active_config()
            execute_command("RELOAD", site=omd_site())
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return ec.default_config()
