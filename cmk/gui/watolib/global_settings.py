#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import cmk.gui.watolib.config_domain_name as config_domain_name
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    UNREGISTERED_SETTINGS,
)


def load_configuration_settings(
    site_specific: bool = False, custom_site_path: str | None = None, full_config: bool = False
) -> GlobalSettings:
    settings = {}
    for domain in ABCConfigDomain.enabled_domains():
        if full_config:
            settings.update(domain().load_full_config())
        elif site_specific:
            settings.update(domain().load_site_globals(custom_site_path=custom_site_path))
        else:
            settings.update(domain().load())
    return settings


def save_global_settings(
    vars_: GlobalSettings, site_specific: bool = False, custom_site_path: str | None = None
) -> None:
    per_domain: dict[str, dict[Any, Any]] = {}
    # TODO: Uee _get_global_config_var_names() from domain class?
    for config_variable_class in config_variable_registry.values():
        config_variable = config_variable_class()
        domain = config_variable.domain()
        varname = config_variable.ident()
        if varname not in vars_:
            continue
        per_domain.setdefault(domain().ident(), {})[varname] = vars_[varname]

    # Some settings are handed over from the central site but are not registered in the
    # configuration domains since the user must not change it directly.
    for varname in UNREGISTERED_SETTINGS:
        if varname in vars_:
            per_domain.setdefault(config_domain_name.GUI, {})[varname] = vars_[varname]

    for domain in ABCConfigDomain.enabled_domains():
        domain_config = per_domain.get(domain().ident(), {})
        if site_specific:
            domain().save_site_globals(domain_config, custom_site_path=custom_site_path)
        else:
            domain().save(domain_config, custom_site_path=custom_site_path)


def load_site_global_settings(custom_site_path: str | None = None) -> GlobalSettings:
    return load_configuration_settings(site_specific=True, custom_site_path=custom_site_path)


def save_site_global_settings(
    settings: GlobalSettings, custom_site_path: str | None = None
) -> None:
    save_global_settings(settings, site_specific=True, custom_site_path=custom_site_path)
