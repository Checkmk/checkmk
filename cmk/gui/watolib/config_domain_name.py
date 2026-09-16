#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"


import abc
import os
import pprint
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, NewType, override, TypedDict

import cmk.ccc.plugin_registry
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.type_defs import GlobalSettings, GraphTimerange
from cmk.gui.watolib.site_changes import ChangeSpec
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import IconNames
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.speaklater import LazyString

ConfigDomainName = str

RemoveIn310 = NewType("RemoveIn310", ConfigDomainName)
"""Marks a previous config domain ident still sent by 2.5 central sites.

3.0 is the last version to accept it: delete this type once 3.1 has branched off."""

CORE: Final[ConfigDomainName] = "check_mk"
GUI: Final[ConfigDomainName] = "multisite"
CA_CERTIFICATES: Final[ConfigDomainName] = "ca-certificates"
SITE_CERTIFICATE: Final[ConfigDomainName] = "site-certificate"
OMD: Final[ConfigDomainName] = "omd"
EVENT_CONSOLE: Final[ConfigDomainName] = "ec"


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
    settings: SerializedSettings = field(default_factory=lambda: SerializedSettings({}))


DomainRequests = Sequence[DomainRequest]


class ABCConfigDomain(abc.ABC):
    """
    always_activate:
        this attribute is used to determine if a config domain needs to be
        activated regardless of the change type.
        Pass ``domains=[]`` to :meth:`PendingChanges.add` to have more granular
        control.

    in_global_settings:
        whether the global settings page lists this domain's configuration variables.
        Domains with a settings page of their own set it to false; their variables
        stay editable there and via the REST API.

    global_settings_permission:
        the permission needed to read or change this domain's configuration variables,
        centrally as well as per site.
    """

    needs_sync = True
    needs_activation = True
    always_activate = False
    in_global_settings = True
    global_settings_permission: PermissionName = "wato.global"

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> ConfigDomainName: ...

    @classmethod
    def previous_idents(cls) -> Sequence[RemoveIn310]:
        """Idents this domain has been registered under before.

        Activation uses the idents on the wire, not just in the payload. This means idents are not
        affected by `cmk-update-config`. We translate these old identifiers on the fly, since they
        may still be sent by the central site."""
        return ()

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
        raise NotImplementedError

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
            raise MKGeneralException(
                _("Cannot read configuration file %(filename)s: %(e)s")
                % {"filename": filename, "e": e}
            )

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

    @contextmanager
    def settings_change(
        self,
        sites: SiteConfigurations,  # noqa: ARG002
        before: Mapping[SiteId, GlobalSettings],  # noqa: ARG002
        after: Mapping[SiteId, GlobalSettings],  # noqa: ARG002
    ) -> Iterator[None]:
        """Wrap the write of a settings change with the settings in effect for every site.

        Before the yield nothing is written yet, and a domain can reject a combination it
        cannot serve by raising MKUserError. After the yield the change is on disk, and a
        domain reacts to it, for example by logging security events. Most domains do neither.
        """
        yield

    @abc.abstractmethod
    def default_globals(self) -> GlobalSettings:
        """Returns a dictionary that contains the default settings
        of all configuration variables of this config domain."""
        raise NotImplementedError

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
    def get_domain_request(cls, settings: list[SerializedSettings]) -> DomainRequest:  # noqa: ARG003
        return DomainRequest(cls.ident())

    @classmethod
    def hint(cls) -> HTML:
        return HTML.empty()


@request_memoize()
def _get_all_default_globals() -> GlobalSettings:  # type: ignore[misc]
    settings: dict[str, Any] = {}
    for domain in ABCConfigDomain.enabled_domains():
        settings.update(domain.default_globals())
    return settings


def get_config_domain(domain_ident: ConfigDomainName) -> ABCConfigDomain:
    return config_domain_registry[domain_ident]


def get_always_activate_domains() -> Sequence[ABCConfigDomain]:
    return [d for d in config_domain_registry.values() if d.always_activate]


class ConfigDomainRegistry(cmk.ccc.plugin_registry.Registry[ABCConfigDomain]):
    @override
    def plugin_name(self, instance: ABCConfigDomain) -> str:
        return instance.ident()

    def renamed_ident(self, previous_ident: ConfigDomainName) -> ConfigDomainName | None:
        """The current ident of the domain formerly registered under the given one."""
        for domain in self.values():
            if previous_ident in domain.previous_idents():
                return domain.ident()
        return None


config_domain_registry = ConfigDomainRegistry()


def generate_hosts_to_update_settings(hostnames: Sequence[HostName]) -> SerializedSettings:
    return {"hosts_to_update": hostnames}


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
        self,
        *,
        title: LazyString,
        sort_index: int,
        warning: LazyString | None = None,
        icon: IconNames = IconNames.configuration,
        description: LazyString | None = None,
    ) -> None:
        self._title = title
        self._sort_index = sort_index
        self._warning = warning
        self._icon = icon
        self._description = description

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

    def icon(self) -> IconNames:
        return self._icon

    def description(self) -> str:
        return str(self._description) if self._description else ""

    def config_variables(self) -> list[ConfigVariable]:
        """Returns a list of configuration variable classes that belong to this group"""
        return [v for v in config_variable_registry.values() if v.group() == self]


class ConfigVariableGroupRegistry(cmk.ccc.plugin_registry.Registry[ConfigVariableGroup]):
    @override
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


@dataclass(frozen=True)
class ConfigVariableHint:
    text: HTML
    variant: Literal["info", "warning"] = "warning"
    copyable: str | None = None
    """Value the frontend shows behind the text with a control that copies it."""


class ConfigVariable:
    def __init__(
        self,
        *,
        group: ConfigVariableGroup,
        primary_domain: type[ABCConfigDomain],
        ident: str,
        form_spec: Callable[[GlobalSettingsContext], FormSpec[Any]],
        need_restart: bool | None = None,
        need_apache_reload: bool = False,
        allow_reset: bool = True,
        in_global_settings: bool = True,
        hints: Callable[[], Sequence[ConfigVariableHint]] = tuple,
    ) -> None:
        self._group = group
        self._primary_domain_ident = primary_domain.ident()
        self._ident = ident
        self._form_spec_func = form_spec
        self._need_restart = need_restart
        self._need_apache_reload = need_apache_reload
        self._allow_reset = allow_reset
        self._in_global_settings = in_global_settings
        self._hints = hints
        self._idents_of_affected_domains = [self._primary_domain_ident]

    def group(self) -> ConfigVariableGroup:
        """Returns the the configuration variable group this configuration variable belongs to"""
        return self._group

    def ident(self) -> str:
        """Returns the internal identifier of this configuration variable"""
        return self._ident

    def value_model(self, context: GlobalSettingsContext) -> FormSpec[Any]:
        """Returns the FormSpec representing the value model of this configuration variable"""
        return self._form_spec_func(context)

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

    def hints(self) -> Sequence[ConfigVariableHint]:
        domain_hint = self.primary_domain().hint()
        return [*([ConfigVariableHint(domain_hint)] if domain_hint else []), *self._hints()]

    def add_config_domain_affected_by_change(
        self,
        domain: type[ABCConfigDomain],
    ) -> None:
        if (domain_ident := domain.ident()) not in self._idents_of_affected_domains:
            self._idents_of_affected_domains.append(domain_ident)


class ConfigVariableRegistry(cmk.ccc.plugin_registry.Registry[ConfigVariable]):
    @override
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
    "authentication_connections",
    "user_attribute_sync_connections",
}


def filter_unknown_settings(settings: GlobalSettings) -> GlobalSettings:
    known_settings = set(config_variable_registry) | UNREGISTERED_SETTINGS
    return {k: v for k, v in settings.items() if k in known_settings}


def finalize_specifically_set_settings(
    global_settings: GlobalSettings, site_specific_settings: GlobalSettings
) -> GlobalSettings:
    return {**global_settings, **site_specific_settings}


def finalize_all_settings(
    default_globals: GlobalSettings,
    global_settings: GlobalSettings,
    site_specific_settings: GlobalSettings,
) -> GlobalSettings:
    return {
        **default_globals,
        **finalize_specifically_set_settings(global_settings, site_specific_settings),
    }


def finalize_all_settings_per_site(
    default_globals: GlobalSettings,
    global_settings: GlobalSettings,
    site_specific_settings_per_site: Mapping[SiteId, GlobalSettings],
) -> Mapping[SiteId, GlobalSettings]:
    return {
        site_id: finalize_all_settings(default_globals, global_settings, site_conf)
        for site_id, site_conf in site_specific_settings_per_site.items()
    }


def configvar_order() -> dict[str, int]:
    raise NotImplementedError(
        "Please don't use this API anymore. Have a look at werk #6911 for further information."
    )
