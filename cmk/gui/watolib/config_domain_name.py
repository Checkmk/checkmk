#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import abc
import os
import pprint
from collections.abc import Callable, Generator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, TypedDict

from livestatus import SiteConfigurations

import cmk.ccc.plugin_registry
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.type_defs import (
    GlobalSettings,
    GraphTimerange,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import ValueSpec
from cmk.gui.watolib.site_changes import ChangeSpec
from cmk.utils.config_warnings import ConfigurationWarnings

ConfigDomainName = str

CORE: Final[ConfigDomainName] = "check_mk"
GUI: Final[ConfigDomainName] = "multisite"
LIVEPROXY: Final[ConfigDomainName] = "liveproxyd"
CA_CERTIFICATES: Final[ConfigDomainName] = "ca-certificates"
SITE_CERTIFICATE: Final[ConfigDomainName] = "site-certificate"
OMD: Final[ConfigDomainName] = "omd"


def wato_fileheader() -> str:
    return "# Created by WATO\n\n"


class PasswordChange(TypedDict, total=True):
    change_type: Literal["ADD", "EDIT", "DELETE"]
    password_id: str


class SerializedSettings(TypedDict, total=False):
    hosts_to_update: Sequence[HostName]
    need_apache_reload: bool
    changed_passwords: Sequence[PasswordChange]


DomainSettings = Mapping[ConfigDomainName, SerializedSettings]


@dataclass
class DomainRequest:
    name: str
    settings: SerializedSettings = field(default_factory=lambda: SerializedSettings(dict()))


DomainRequests = Sequence[DomainRequest]


class ABCConfigDomain(abc.ABC):
    """
    always_activate:
        this attribute is used to determine if a config domain needs to be
        activated regardless of the change type.
        Use :func:`~cmk.gui.watolib.changes.add_change(domains=[])` to have more granular
        control
    """

    needs_sync = True
    needs_activation = True
    always_activate = False
    in_global_settings = True

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> ConfigDomainName: ...

    @classmethod
    def enabled_domains(cls) -> Sequence[ABCConfigDomain]:
        return [d for d in config_domain_registry.values() if d.enabled()]

    @abc.abstractmethod
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        """
        This allows us to ensure that some artifacts are created by one domain
        that are needed by the activation of another domain.
        """

    @abc.abstractmethod
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings: ...

    @classmethod
    def enabled(cls) -> bool:
        return True

    @classmethod
    def get_all_default_globals(cls) -> GlobalSettings:
        return _get_all_default_globals()

    @abc.abstractmethod
    def config_dir(self) -> Path:
        raise NotImplementedError()

    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / ("sitespecific.mk" if site_specific else "global.mk")

    def load_full_config(
        self, site_specific: bool = False, custom_site_path: str | None = None
    ) -> GlobalSettings:
        filename = self.config_file(site_specific)
        if custom_site_path:
            filename = Path(custom_site_path) / filename.relative_to(cmk.utils.paths.omd_root)

        settings: dict[str, Any] = {}

        if not filename.exists():
            return {}

        try:
            with filename.open("rb") as f:
                exec(f.read(), {}, settings)  # nosec B102 # BNS:aee528

            return settings

        except Exception as e:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (filename, e))

    def load(
        self, site_specific: bool = False, custom_site_path: str | None = None
    ) -> GlobalSettings:
        return filter_unknown_settings(self.load_full_config(site_specific, custom_site_path))

    def load_site_globals(self, custom_site_path: str | None = None) -> GlobalSettings:
        return self.load(site_specific=True, custom_site_path=custom_site_path)

    def save(
        self,
        settings: GlobalSettings,
        site_specific: bool = False,
        custom_site_path: str | None = None,
    ) -> None:
        filename = self.config_file(site_specific)
        if custom_site_path:
            filename = Path(custom_site_path) / os.path.relpath(filename, cmk.utils.paths.omd_root)

        output = wato_fileheader()
        for varname, value in settings.items():
            output += f"{varname} = {pprint.pformat(value)}\n"

        filename.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_text_to_file(filename, output)

    def save_site_globals(
        self, settings: GlobalSettings, custom_site_path: str | None = None
    ) -> None:
        self.save(settings, site_specific=True, custom_site_path=custom_site_path)

    @abc.abstractmethod
    def default_globals(self) -> GlobalSettings:
        """Returns a dictionary that contains the default settings
        of all configuration variables of this config domain."""
        raise NotImplementedError()

    def _get_global_config_var_names(self) -> list[str]:
        """Returns a list of all global config variable names
        associated with this config domain."""
        return [
            varname
            for (varname, v) in config_variable_registry.items()
            if v.primary_domain().ident() == self.ident()
        ]

    @classmethod
    def get_domain_settings(cls, change: ChangeSpec) -> SerializedSettings:
        return change.get("domain_settings", {}).get(cls.ident(), {})

    @classmethod
    def get_domain_request(cls, settings: list[SerializedSettings]) -> DomainRequest:
        return DomainRequest(cls.ident())

    @classmethod
    def hint(cls) -> HTML:
        return HTML.empty()


@request_memoize()
def _get_all_default_globals() -> GlobalSettings:
    settings: dict[str, Any] = {}
    for domain in ABCConfigDomain.enabled_domains():
        settings.update(domain.default_globals())
    return settings


def get_config_domain(domain_ident: ConfigDomainName) -> ABCConfigDomain:
    return config_domain_registry[domain_ident]


def get_always_activate_domains() -> Sequence[ABCConfigDomain]:
    return [d for d in config_domain_registry.values() if d.always_activate]


class ConfigDomainRegistry(cmk.ccc.plugin_registry.Registry[ABCConfigDomain]):
    def plugin_name(self, instance: ABCConfigDomain) -> str:
        return instance.ident()


config_domain_registry = ConfigDomainRegistry()


def generate_hosts_to_update_settings(hostnames: Sequence[HostName]) -> SerializedSettings:
    return {"hosts_to_update": hostnames}


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


class SampleConfigGeneratorRegistry(cmk.ccc.plugin_registry.Registry[type[SampleConfigGenerator]]):
    def plugin_name(self, instance: type[SampleConfigGenerator]) -> str:
        return instance.ident()

    def get_generators(self) -> list[SampleConfigGenerator]:
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
#   |  not only needed by the Setup for mode for editing these, but e.g.    |
#   |  also in the code for distributed Setup (handling of site specific    |
#   |  globals).
#   '----------------------------------------------------------------------'


class ConfigVariableGroup:
    def __init__(
        self, *, title: LazyString, sort_index: int, warning: LazyString | None = None
    ) -> None:
        self._title = title
        self._sort_index = sort_index
        self._warning = warning

    # TODO: The identity of a configuration variable group should be a pure
    # internal unique key and it should not be localized. The title of a
    # group was always used as identity. Check all call sites and introduce
    # internal IDs in case it is sure that we can change it without bad side
    # effects.
    def ident(self) -> str:
        """Unique internal key of this group"""
        return str(self._title)

    def title(self) -> str:
        """Human readable title of this group"""
        return str(self._title)

    def sort_index(self) -> int:
        """Returns an integer to control the sorting of the groups in lists"""
        return self._sort_index

    def warning(self) -> str | None:
        """Return a string if you want to show a warning at the top of this group"""
        return str(self._warning) if self._warning else None

    def config_variables(self) -> list[ConfigVariable]:
        """Returns a list of configuration variable classes that belong to this group"""
        return [v for v in config_variable_registry.values() if v.group() == self]


class ConfigVariableGroupRegistry(cmk.ccc.plugin_registry.Registry[ConfigVariableGroup]):
    def plugin_name(self, instance: ConfigVariableGroup) -> str:
        return instance.ident()


config_variable_group_registry = ConfigVariableGroupRegistry()


@dataclass(frozen=True)
class GlobalSettingsContext:
    target_site_id: SiteId
    edition_of_local_site: Edition
    site_neutral_log_dir: Path
    site_neutral_var_dir: Path
    configured_sites: SiteConfigurations
    configured_graph_timeranges: Sequence[GraphTimerange]


class ConfigVariable:
    def __init__(
        self,
        *,
        group: ConfigVariableGroup,
        primary_domain: type[ABCConfigDomain],
        ident: str,
        valuespec: Callable[[GlobalSettingsContext], ValueSpec],
        need_restart: bool | None = None,
        need_apache_reload: bool = False,
        allow_reset: bool = True,
        in_global_settings: bool = True,
        hint: Callable[[], HTML] = lambda: HTML.empty(),
        domain_hint: HTML = HTML.empty(),
    ) -> None:
        self._group = group
        self._primary_domain_ident = primary_domain.ident()
        self._ident = ident
        self._valuespec_func = valuespec
        self._need_restart = need_restart
        self._need_apache_reload = need_apache_reload
        self._allow_reset = allow_reset
        self._in_global_settings = in_global_settings
        self._hint_func = hint
        self._domain_hint = domain_hint
        self._idents_of_affected_domains = [self._primary_domain_ident]

    def group(self) -> ConfigVariableGroup:
        """Returns the the configuration variable group this configuration variable belongs to"""
        return self._group

    def ident(self) -> str:
        """Returns the internal identifier of this configuration variable"""
        return self._ident

    def valuespec(self, context: GlobalSettingsContext) -> ValueSpec:
        """Returns the valuespec object of this configuration variable"""
        return self._valuespec_func(context)

    def primary_domain(self) -> ABCConfigDomain:
        """Returns the config domain this configuration variable belongs to"""
        return config_domain_registry[self._primary_domain_ident]

    def all_domains(self) -> Generator[ABCConfigDomain]:
        yield from (
            config_domain_registry[domain_ident]
            for domain_ident in self._idents_of_affected_domains
        )

    # TODO: This is boolean flag which defaulted to None in case a variable declaration did not
    # provide this attribute.
    # Investigate:
    # - Is this needed per config variable or do we need this only per config domain?
    # - Can't we simplify this to simply be a boolean?
    def need_restart(self) -> bool | None:
        """Whether or not a change to this setting enforces a "restart" during activate changes instead of just a synchronization"""
        return self._need_restart

    def need_apache_reload(self) -> bool:
        """Whether a change to this setting enforces an apache reload, this currently only works when using the ConfigDomainGUI"""
        return self._need_apache_reload

    # TODO: Investigate: Which use cases do we have here? Can this be dropped?
    def allow_reset(self) -> bool:
        """Whether or not the user is allowed to change this setting to factory settings"""
        return self._allow_reset

    def in_global_settings(self) -> bool:
        """Whether or not to show this option on the global settings page"""
        return self._in_global_settings

    def hint(self) -> HTML:
        return self._hint_func()

    def domain_hint(self) -> HTML:
        return self._domain_hint

    def add_config_domain_affected_by_change(
        self,
        domain: type[ABCConfigDomain],
    ) -> None:
        if (domain_ident := domain.ident()) not in self._idents_of_affected_domains:
            self._idents_of_affected_domains.append(domain_ident)


class ConfigVariableRegistry(cmk.ccc.plugin_registry.Registry[ConfigVariable]):
    def plugin_name(self, instance: ConfigVariable) -> str:
        return instance.ident()


config_variable_registry = ConfigVariableRegistry()


# Some settings are handed over from the central site but are not registered in the
# configuration domains since the user must not change it directly. They all belong
# to the GUI config domain.
UNREGISTERED_SETTINGS = {
    "wato_enabled",
    "userdb_automatic_sync",
    "user_login",
}


def filter_unknown_settings(settings: GlobalSettings) -> GlobalSettings:
    known_settings = set(config_variable_registry) | UNREGISTERED_SETTINGS
    return {k: v for k, v in settings.items() if k in known_settings}


def configvar_order() -> dict[str, int]:
    raise NotImplementedError(
        "Please don't use this API anymore. Have a look at werk #6911 for further information."
    )
