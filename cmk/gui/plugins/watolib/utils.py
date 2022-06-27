#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
import pprint
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Type

import cmk.utils.plugin_registry
import cmk.utils.store as store
from cmk.utils.type_defs import ConfigurationWarnings

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.type_defs import ConfigDomainName
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import ValueSpec


def wato_fileheader() -> str:
    return "# Created by WATO\n\n"


SerializedSettings = Mapping[str, Any]
DomainSettings = Mapping[ConfigDomainName, SerializedSettings]


@dataclass
class DomainRequest:
    name: str
    settings: SerializedSettings = field(default_factory=dict)


DomainRequests = Sequence[DomainRequest]


class ABCConfigDomain(abc.ABC):
    needs_sync = True
    needs_activation = True
    always_activate = False
    in_global_settings = True

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> ConfigDomainName:
        ...

    @classmethod
    def enabled_domains(cls):
        return [d for d in config_domain_registry.values() if d.enabled()]

    @abc.abstractmethod
    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        raise MKGeneralException(_('The domain "%s" does not support activation.') % self.ident())

    @classmethod
    def get_class(cls, ident):
        return config_domain_registry[ident]

    @classmethod
    def enabled(cls):
        return True

    @classmethod
    def get_all_default_globals(cls) -> Dict[str, Any]:
        return _get_all_default_globals()

    @abc.abstractmethod
    def config_dir(self):
        raise NotImplementedError()

    def config_file(self, site_specific):
        if site_specific:
            return os.path.join(self.config_dir(), "sitespecific.mk")
        return os.path.join(self.config_dir(), "global.mk")

    def load_full_config(self, site_specific=False, custom_site_path=None):
        filename = Path(self.config_file(site_specific))
        if custom_site_path:
            filename = Path(custom_site_path) / filename.relative_to(cmk.utils.paths.omd_root)

        settings: Dict[str, Any] = {}

        if not filename.exists():
            return {}

        try:
            with filename.open("rb") as f:
                exec(f.read(), settings, settings)

            return settings

        except Exception as e:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (filename, e))

    def load(self, site_specific=False, custom_site_path=None):
        return filter_unknown_settings(self.load_full_config(site_specific, custom_site_path))

    def load_site_globals(self, custom_site_path=None):
        return self.load(site_specific=True, custom_site_path=custom_site_path)

    def save(self, settings, site_specific=False, custom_site_path=None):
        filename = self.config_file(site_specific)
        if custom_site_path:
            filename = os.path.join(
                custom_site_path, os.path.relpath(filename, cmk.utils.paths.omd_root)
            )

        output = wato_fileheader()
        for varname, value in settings.items():
            output += "%s = %s\n" % (varname, pprint.pformat(value))

        store.makedirs(os.path.dirname(filename))
        store.save_text_to_file(filename, output)

    def save_site_globals(self, settings, custom_site_path=None):
        self.save(settings, site_specific=True, custom_site_path=custom_site_path)

    @abc.abstractmethod
    def default_globals(self):
        """Returns a dictionary that contains the default settings
        of all configuration variables of this config domain."""
        raise NotImplementedError()

    def _get_global_config_var_names(self):
        """Returns a list of all global config variable names
        associated with this config domain."""
        return [
            varname
            for (varname, v) in config_variable_registry.items()
            if v().domain() == self.__class__
        ]

    @classmethod
    def get_domain_settings(cls, change) -> SerializedSettings:
        return change.get("domain_settings", {}).get(cls.ident(), {})

    @classmethod
    def get_domain_request(cls, settings: List[SerializedSettings]) -> DomainRequest:
        return DomainRequest(cls.ident())


@request_memoize()
def _get_all_default_globals() -> Dict[str, Any]:
    settings: Dict[str, Any] = {}
    for domain in ABCConfigDomain.enabled_domains():
        settings.update(domain().default_globals())
    return settings


def get_config_domain(domain_ident: ConfigDomainName):
    return config_domain_registry[domain_ident]


def get_always_activate_domains() -> Sequence[Type[ABCConfigDomain]]:
    return [d for d in config_domain_registry.values() if d.always_activate]


class ConfigDomainRegistry(cmk.utils.plugin_registry.Registry[Type[ABCConfigDomain]]):
    def plugin_name(self, instance):
        return instance.ident()


config_domain_registry = ConfigDomainRegistry()


class SampleConfigGenerator(abc.ABC):
    @classmethod
    def ident(cls) -> str:
        """Unique key which can be used to identify a generator"""
        raise NotImplementedError()

    # TODO: @abc.abstractmethod
    @classmethod
    def sort_index(cls) -> int:
        """The generators are executed in this order (low to high)"""
        raise NotImplementedError()

    @abc.abstractmethod
    def generate(self) -> None:
        """Execute the sample configuration creation step"""
        raise NotImplementedError()


class SampleConfigGeneratorRegistry(
    cmk.utils.plugin_registry.Registry[Type[SampleConfigGenerator]]
):
    def plugin_name(self, instance):
        return instance.ident()

    def get_generators(self) -> List[SampleConfigGenerator]:
        """Return the generators in the order they are expected to be executed"""
        return sorted([g_class() for g_class in self.values()], key=lambda e: e.sort_index())


sample_config_generator_registry = SampleConfigGeneratorRegistry()

# .
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


class ConfigVariableGroup:
    # TODO: The identity of a configuration variable group should be a pure
    # internal unique key and it should not be localized. The title of a
    # group was always used as identity. Check all call sites and introduce
    # internal IDs in case it is sure that we can change it without bad side
    # effects.
    def ident(self) -> str:
        """Unique internal key of this group"""
        return self.title()

    def title(self) -> str:
        """Human readable title of this group"""
        raise NotImplementedError()

    def sort_index(self) -> int:
        """Returns an integer to control the sorting of the groups in lists"""
        raise NotImplementedError()

    def config_variables(self) -> "List[Type[ConfigVariable]]":
        """Returns a list of configuration variable classes that belong to this group"""
        return [v for v in config_variable_registry.values() if v().group() == self.__class__]


class ConfigVariableGroupRegistry(cmk.utils.plugin_registry.Registry[Type[ConfigVariableGroup]]):
    def plugin_name(self, instance):
        return instance().ident()


config_variable_group_registry = ConfigVariableGroupRegistry()


class ConfigVariable:
    def group(self) -> Type[ConfigVariableGroup]:
        """Returns the class of the configuration variable group this configuration variable belongs to"""
        raise NotImplementedError()

    def ident(self) -> str:
        """Returns the internal identifier of this configuration variable"""
        raise NotImplementedError()

    def valuespec(self) -> ValueSpec:
        """Returns the valuespec object of this configuration variable"""
        raise NotImplementedError()

    def domain(self) -> Type[ABCConfigDomain]:
        """Returns the class of the config domain this configuration variable belongs to"""
        return config_domain_registry["check_mk"]

    # TODO: This is boolean flag which defaulted to None in case a variable declaration did not
    # provide this attribute.
    # Investigate:
    # - Is this needed per config variable or do we need this only per config domain?
    # - Can't we simplify this to simply be a boolean?
    def need_restart(self) -> Optional[bool]:
        """Whether or not a change to this setting enforces a "restart" during activate changes instead of just a synchronization"""
        return None

    # TODO: Investigate: Which use cases do we have here? Can this be dropped?
    def allow_reset(self) -> bool:
        """Whether or not the user is allowed to change this setting to factory settings"""
        return True

    def in_global_settings(self) -> bool:
        """Whether or not to show this option on the global settings page"""
        return True

    def hint(self) -> HTML:
        return HTML()


class ConfigVariableRegistry(cmk.utils.plugin_registry.Registry[Type[ConfigVariable]]):
    def plugin_name(self, instance):
        return instance().ident()


config_variable_registry = ConfigVariableRegistry()


def filter_unknown_settings(settings):
    removals: List[str] = []
    for varname in list(settings.keys()):
        if varname not in config_variable_registry:
            removals.append(varname)
    for removal in removals:
        del settings[removal]
    return settings


def configvar_order() -> dict[str, int]:
    raise NotImplementedError(
        "Please don't use this API anymore. Have a look at werk #6911 for further information."
    )


# TODO: This function has been replaced with config_variable_registry and
# ConfigVariable() in 1.6. Drop this API with 1.7 latest.
def register_configvar(
    group,
    varname,
    valuespec,
    domain=None,
    need_restart=None,
    allow_reset=True,
    in_global_settings=True,
):

    if domain is None:
        domain = config_domain_registry["check_mk"]

    # New API is to hand over the class via domain argument. But not all calls have been
    # migrated. Perform the translation here.
    if isinstance(domain, str):
        domain = get_config_domain(domain)

    # New API is to hand over the class via group argument
    if isinstance(group, str):
        group = config_variable_group_registry[group]

    cls = type(
        "LegacyConfigVariable%s" % varname.title(),
        (ConfigVariable,),
        {
            "group": lambda self: group,
            "ident": lambda self: varname,
            "valuespec": lambda self: valuespec,
            "domain": lambda self: domain,
            "need_restart": lambda self: need_restart,
            "allow_reset": lambda self: allow_reset,
            "in_global_settings": lambda self: in_global_settings,
        },
    )
    config_variable_registry.register(cls)
