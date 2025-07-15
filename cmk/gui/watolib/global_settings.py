#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any

from cmk.ccc.version import Edition, edition

from cmk.utils import paths

from cmk.gui.global_config import get_global_config, GlobalConfig
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib import config_domain_name
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    UNREGISTERED_SETTINGS,
)


def load_configuration_settings(
    site_specific: bool = False, custom_site_path: str | None = None, full_config: bool = False
) -> GlobalSettings:
    settings: dict[str, Any] = {}
    for domain in ABCConfigDomain.enabled_domains():
        if full_config:
            settings.update(domain.load_full_config())
        elif site_specific:
            settings.update(domain.load_site_globals(custom_site_path=custom_site_path))
        else:
            settings.update(domain.load())
    return settings


def save_global_settings(
    vars_: GlobalSettings,
    site_specific: bool = False,
    custom_site_path: str | None = None,
    get_global_settings_config: Callable[[], GlobalConfig] = get_global_config,
    skip_cse_edition_check: bool = False,
) -> None:
    if not skip_cse_edition_check and edition(paths.omd_root) is Edition.CSE:
        global_settings_config = get_global_settings_config().global_settings
        current_global_settings = dict(load_configuration_settings())
        vars_ = {
            varname: (
                value
                if global_settings_config.is_activated(varname)
                else current_global_settings[varname]
            )
            for varname, value in vars_.items()
            if global_settings_config.is_activated(varname) or varname in current_global_settings
        }

    per_domain: dict[str, dict[Any, Any]] = {}
    # TODO: Uee _get_global_config_var_names() from domain class?
    for config_variable in config_variable_registry.values():
        domain = config_variable.domain()
        varname = config_variable.ident()
        if varname not in vars_:
            continue
        per_domain.setdefault(domain.ident(), {})[varname] = vars_[varname]

    # Some settings are handed over from the central site but are not registered in the
    # configuration domains since the user must not change it directly.
    for varname in UNREGISTERED_SETTINGS:
        if varname in vars_:
            per_domain.setdefault(config_domain_name.GUI, {})[varname] = vars_[varname]

    for domain in ABCConfigDomain.enabled_domains():
        domain_config = per_domain.get(domain.ident(), {})
        if site_specific:
            domain.save_site_globals(domain_config, custom_site_path=custom_site_path)
        else:
            domain.save(domain_config, custom_site_path=custom_site_path)


def load_site_global_settings(custom_site_path: str | None = None) -> GlobalSettings:
    return load_configuration_settings(site_specific=True, custom_site_path=custom_site_path)


def save_site_global_settings(
    settings: GlobalSettings, custom_site_path: str | None = None
) -> None:
    save_global_settings(settings, site_specific=True, custom_site_path=custom_site_path)
