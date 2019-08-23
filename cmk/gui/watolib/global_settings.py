#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_variable_registry,
)


def load_configuration_settings(site_specific=False):
    settings = {}
    for domain in ABCConfigDomain.enabled_domains():
        if site_specific:
            settings.update(domain().load_site_globals())
        else:
            settings.update(domain().load())
    return settings


def save_global_settings(vars_, site_specific=False):
    per_domain = {}
    # TODO: Uee _get_global_config_var_names() from domain class?
    for config_variable_class in config_variable_registry.values():
        config_variable = config_variable_class()
        domain = config_variable.domain()
        varname = config_variable.ident()
        if varname not in vars_:
            continue
        per_domain.setdefault(domain.ident, {})[varname] = vars_[varname]

    # The global setting wato_enabled is not registered in the configuration domains
    # since the user must not change it directly. It is set by D-WATO on slave sites.
    if "wato_enabled" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident, {})["wato_enabled"] = vars_["wato_enabled"]
    if "userdb_automatic_sync" in vars_:
        per_domain.setdefault(ConfigDomainGUI.ident,
                              {})["userdb_automatic_sync"] = vars_["userdb_automatic_sync"]

    for domain in ABCConfigDomain.enabled_domains():
        if site_specific:
            domain().save_site_globals(per_domain.get(domain.ident, {}))
        else:
            domain().save(per_domain.get(domain.ident, {}))


def save_site_global_settings(vars_):
    save_global_settings(vars_, site_specific=True)
