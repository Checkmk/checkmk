#!/usr/bin/env python
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

import os
import pprint

import cmk.store as store

import cmk.plugin_registry
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException


def wato_fileheader():
    return "# Created by WATO\n# encoding: utf-8\n\n"


class ConfigDomain(object):
    needs_sync = True
    needs_activation = True
    always_activate = False
    ident = None
    in_global_settings = True

    @classmethod
    def enabled_domains(cls):
        return [d for d in config_domain_registry.values() if d.enabled()]

    @classmethod
    def get_always_activate_domain_idents(cls):
        return [d.ident for d in config_domain_registry.values() if d.always_activate]

    @classmethod
    def get_class(cls, ident):
        return config_domain_registry[ident]

    @classmethod
    def enabled(cls):
        return True

    @classmethod
    def get_all_default_globals(cls):
        settings = {}
        for domain in ConfigDomain.enabled_domains():
            settings.update(domain().default_globals())
        return settings

    def config_dir(self):
        raise NotImplementedError()

    def config_file(self, site_specific):
        if site_specific:
            return os.path.join(self.config_dir(), "sitespecific.mk")
        return os.path.join(self.config_dir(), "global.mk")

    def activate(self):
        raise MKGeneralException(_("The domain \"%s\" does not support activation.") % self.ident)

    def load(self, site_specific=False):
        filename = self.config_file(site_specific)
        settings = {}

        if not os.path.exists(filename):
            return {}

        try:
            execfile(filename, settings, settings)

            # FIXME: Do not modify the dict while iterating over it.
            for varname in list(settings.keys()):
                if varname not in _configvars:
                    del settings[varname]

            return settings
        except Exception as e:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (filename, e))

    def load_site_globals(self):
        return self.load(site_specific=True)

    def save(self, settings, site_specific=False):
        filename = self.config_file(site_specific)

        output = wato_fileheader()
        for varname, value in settings.items():
            output += "%s = %s\n" % (varname, pprint.pformat(value))

        store.makedirs(os.path.dirname(filename))
        store.save_file(filename, output)

    def save_site_globals(self, settings):
        self.save(settings, site_specific=True)

    def default_globals(self):
        """Returns a dictionary that contains the default settings
        of all configuration variables of this config domain."""
        raise NotImplementedError()

    def _get_global_config_var_names(self):
        """Returns a list of all global config variable names
        associated with this config domain."""
        return [varname for (varname, var) in configvars().items() if var[0] == self.__class__]


class ConfigDomainRegistry(cmk.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return ConfigDomain

    def _register(self, plugin_class):
        self._entries[plugin_class.ident] = plugin_class


config_domain_registry = ConfigDomainRegistry()

#.
#   .--Global configuration------------------------------------------------.
#   |       ____ _       _           _                    __ _             |
#   |      / ___| | ___ | |__   __ _| |   ___ ___  _ __  / _(_) __ _       |
#   |     | |  _| |/ _ \| '_ \ / _` | |  / __/ _ \| '_ \| |_| |/ _` |      |
#   |     | |_| | | (_) | |_) | (_| | | | (_| (_) | | | |  _| | (_| |      |
#   |      \____|_|\___/|_.__/ \__,_|_|  \___\___/|_| |_|_| |_|\__, |      |
#   |                                                          |___/       |
#   +----------------------------------------------------------------------+
#   |  Code for loading and saving global configuration variables. This is |
#   |  not only needed by the WATO for mode for editing these, but e.g.    |
#   |  also in the code for distributed WATO (handling of site specific    |
#   |  globals).
#   '----------------------------------------------------------------------'
# TODO: Refactor to a plugin registry

_configvars = {}
_configvar_groups = {}
_configvar_order = {}


def configvars():
    return _configvars


def configvar_groups():
    return _configvar_groups


def configvar_order():
    return _configvar_order


def configvar_show_in_global_settings(varname):
    try:
        return configvars()[varname][-1]
    except KeyError:
        return False


# domain is one of the ConfigDomain classes
def register_configvar(group,
                       varname,
                       valuespec,
                       domain=None,
                       need_restart=None,
                       allow_reset=True,
                       in_global_settings=True):

    if domain is None:
        domain = config_domain_registry["check_mk"]

    # New API is to hand over the class via domain argument. But not all calls have been
    # migrated. Perform the translation here.
    if isinstance(domain, basestring):
        domain = ConfigDomain.get_class(domain)

    _configvar_groups.setdefault(group, []).append((domain, varname, valuespec))
    _configvars[varname] = domain, valuespec, need_restart, allow_reset, in_global_settings


def register_configvar_group(title, order=None):
    if order is not None:
        configvar_order()[title] = 18
