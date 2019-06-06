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

import abc
import os
import pprint
from typing import Optional, Type, Text, List  # pylint: disable=unused-import

import six

import cmk.utils.store as store

import cmk.utils.plugin_registry
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.valuespec import ValueSpec  # pylint: disable=unused-import


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
                if varname not in config_variable_registry:
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
        return [
            varname for (varname, v) in config_variable_registry.items()
            if v().domain() == self.__class__
        ]


class ConfigDomainRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return ConfigDomain

    def plugin_name(self, plugin_class):
        return plugin_class.ident


config_domain_registry = ConfigDomainRegistry()


class SampleConfigGenerator(object):
    __metaclass__ = abc.ABCMeta

    # Is currently not possible to do this with Python 2.7:
    # TODO: @abc.abstractmethod
    @classmethod
    def ident(cls):
        # type: () -> str
        """Unique key which can be used to identify a generator"""
        raise NotImplementedError()

    # TODO: @abc.abstractmethod
    @classmethod
    def sort_index(cls):
        # type: () -> int
        """The generators are executed in this order (low to high)"""
        raise NotImplementedError()

    @abc.abstractmethod
    def generate(self):
        # type: () -> None
        """Execute the sample configuration creation step"""
        raise NotImplementedError()


class SampleConfigGeneratorRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return SampleConfigGenerator

    def plugin_name(self, plugin_class):
        return plugin_class.ident()

    def get_generators(self):
        # type: () -> List[SampleConfigGenerator]
        """Return the generators in the order they are expected to be executed"""
        return sorted([g_class() for g_class in self.values()], key=lambda e: e.sort_index())


sample_config_generator_registry = SampleConfigGeneratorRegistry()

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


class ConfigVariableGroup(object):
    # TODO: The identity of a configuration variable group should be a pure
    # internal unique key and it should not be localized. The title of a
    # group was always used as identity. Check all call sites and introduce
    # internal IDs in case it is sure that we can change it without bad side
    # effects.
    def ident(self):
        # type: () -> Text
        """Unique internal key of this group"""
        return self.title()

    def title(self):
        # type: () -> Text
        """Human readable title of this group"""
        raise NotImplementedError()

    def sort_index(self):
        # type: () -> int
        """Returns an integer to control the sorting of the groups in lists"""
        raise NotImplementedError()

    def config_variables(self):
        # type: () -> List[ConfigVariable]
        """Returns a list of configuration variable classes that belong to this group"""
        return [v for v in config_variable_registry.values() if v().group() == self.__class__]


class ConfigVariableGroupRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return ConfigVariableGroup

    def plugin_name(self, plugin_class):
        return plugin_class().ident()


config_variable_group_registry = ConfigVariableGroupRegistry()


class ConfigVariable(object):
    def group(self):
        # type () -> Type[ConfigVariableGroup]
        """Returns the class of the configuration variable group this configuration variable belongs to"""
        raise NotImplementedError()

    def ident(self):
        # type: () -> Text
        """Returns the internal identifier of this configuration variable"""
        raise NotImplementedError()

    def valuespec(self):
        # type: () -> ValueSpec
        """Returns the valuespec object of this configuration variable"""
        raise NotImplementedError()

    def domain(self):
        # type: () -> Type[ConfigDomain]
        """Returns the class of the config domain this configuration variable belongs to"""
        return config_domain_registry["check_mk"]

    # TODO: This is boolean flag which defaulted to None in case a variable declaration did not
    # provide this attribute.
    # Investigate:
    # - Is this needed per config variable or do we need this only per config domain?
    # - Can't we simplify this to simply be a boolean?
    def need_restart(self):
        # type: () -> Optional[bool]
        """Whether or not a change to this setting enforces a "restart" during activate changes instead of just a synchronization"""
        return None

    # TODO: Investigate: Which use cases do we have here? Can this be dropped?
    def allow_reset(self):
        # type: () -> bool
        """Whether or not the user is allowed to change this setting to factory settings"""
        return True

    def in_global_settings(self):
        # type: () -> bool
        """Whether or not to show this option on the global settings page"""
        return True


class ConfigVariableRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return ConfigVariable

    def plugin_name(self, plugin_class):
        return plugin_class().ident()


config_variable_registry = ConfigVariableRegistry()


def configvar_order():
    raise NotImplementedError(
        "Please don't use this API anymore. Have a look at werk #6911 for further information.")


# TODO: This function has been replaced with config_variable_registry and
# ConfigVariable() in 1.6. Drop this API with 1.7 latest.
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
    if isinstance(domain, six.string_types):
        domain = ConfigDomain.get_class(domain)

    # New API is to hand over the class via group argument
    if isinstance(group, six.string_types):
        group = config_variable_group_registry[group]

    cls = type(
        "LegacyConfigVariable%s" % varname.title(), (ConfigVariable,), {
            "group": lambda self: group,
            "ident": lambda self: varname,
            "valuespec": lambda self: valuespec,
            "domain": lambda self: domain,
            "need_restart": lambda self: need_restart,
            "allow_reset": lambda self: allow_reset,
            "in_global_settings": lambda self: in_global_settings,
        })
    config_variable_registry.register(cls)
