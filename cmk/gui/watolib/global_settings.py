#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict

from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_variable_registry,
)


def load_configuration_settings(site_specific=False, custom_site_path=None):
    settings = {}
    for domain in ABCConfigDomain.enabled_domains():
        if site_specific:
            settings.update(domain().load_site_globals(custom_site_path=custom_site_path))
        else:
            settings.update(domain().load())
    return settings


def rulebased_notifications_enabled() -> bool:
    return load_configuration_settings().get("enable_rulebased_notifications", False)


def save_global_settings(vars_, site_specific=False, custom_site_path=None):
    per_domain: Dict[str, Dict[Any, Any]] = {}
    # TODO: Uee _get_global_config_var_names() from domain class?
    for config_variable_class in config_variable_registry.values():
        config_variable = config_variable_class()
        domain = config_variable.domain()
        varname = config_variable.ident()
        if varname not in vars_:
            continue
        per_domain.setdefault(domain().ident, {})[varname] = vars_[varname]

    # The global setting wato_enabled is not registered in the configuration domains
    # since the user must not change it directly. It is set by D-WATO on slave sites.
    if "wato_enabled" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident, {})["wato_enabled"] = vars_["wato_enabled"]
    if "userdb_automatic_sync" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident,
                              {})["userdb_automatic_sync"] = vars_["userdb_automatic_sync"]
    if "user_login" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident, {})["user_login"] = vars_["user_login"]

    for domain in ABCConfigDomain.enabled_domains():
        domain_config = per_domain.get(domain().ident, {})
        if site_specific:
            domain().save_site_globals(domain_config, custom_site_path=custom_site_path)
        else:
            domain().save(domain_config, custom_site_path=custom_site_path)


def save_site_global_settings(settings, custom_site_path=None):
    save_global_settings(settings, site_specific=True, custom_site_path=custom_site_path)
