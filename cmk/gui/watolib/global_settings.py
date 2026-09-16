#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager, ExitStack

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition, edition
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.global_config import get_global_config, GlobalConfig
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import GlobalSettings, GraphTimerange
from cmk.gui.user_sites import get_event_console_site_choices
from cmk.gui.watolib import config_domain_name
from cmk.gui.watolib.audit_log import LogMessage, make_audit_log_change_hook
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariable,
    EVENT_CONSOLE,
    finalize_all_settings_per_site,
    GlobalSettingsContext,
    UNREGISTERED_SETTINGS,
)
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook
from cmk.gui.watolib.utils import site_neutral_path
from cmk.livestatus_client import SiteConfigurations
from cmk.shared_typing.global_settings import GlobalSettingsOrigin
from cmk.utils import paths
from cmk.utils.object_diff import make_diff, make_diff_text
from cmk.utils.paths import log_dir, var_dir
from cmk.web.utils.permission_verification import PermissionName

STATIC_PERMISSIONS_GLOBAL_SETTINGS = ["global"]


def may_read(config_variable: ConfigVariable) -> bool:
    return all(user.may(permission) for permission in _read_permissions(config_variable))


def need_read_permission(config_variable: ConfigVariable) -> None:
    for permission in _read_permissions(config_variable):
        user.need_permission(permission)


def need_write_permission(config_variable: ConfigVariable) -> None:
    user.need_permission("wato.edit")
    need_read_permission(config_variable)


def need_site_read_permission(config_variable: ConfigVariable) -> None:
    user.need_permission("wato.sites")
    need_read_permission(config_variable)


def need_site_write_permission(config_variable: ConfigVariable) -> None:
    user.need_permission("wato.edit")
    need_site_read_permission(config_variable)


def _read_permissions(config_variable: ConfigVariable) -> list[PermissionName]:
    permissions = [config_variable.primary_domain().global_settings_permission]
    if config_variable.ident() == "actions":
        permissions.append("wato.add_or_modify_executables")
    return permissions


def affected_sites(config_variable: ConfigVariable) -> list[SiteId] | None:
    """The sites a change has to be activated on; None means all activation sites."""
    if config_variable.primary_domain().ident() == EVENT_CONSOLE:
        return [site_id for site_id, _title in get_event_console_site_choices()]

    return None


def load_configuration_settings(
    site_specific: bool = False, custom_site_path: str | None = None, full_config: bool = False
) -> GlobalSettings:
    settings: dict[str, object] = {}
    for domain in ABCConfigDomain.enabled_domains():
        if full_config:
            settings.update(domain.load_full_config())
        elif site_specific:
            settings.update(domain.load_site_globals(custom_site_path=custom_site_path))
        else:
            settings.update(domain.load())
    return settings


def effective_value(
    settings: Mapping[str, object], varname: str
) -> tuple[object, GlobalSettingsOrigin]:
    """The value in effect and the layer it comes from.

    Writers pass the same mapping they later hand to save_global_settings(),
    which rewrites the whole file, so they need a mutable copy of it.
    """
    if varname in settings:
        return settings[varname], GlobalSettingsOrigin.global_

    return ABCConfigDomain.get_all_default_globals()[varname], GlobalSettingsOrigin.factory


def effective_site_value(
    site_globals: Mapping[str, object],
    varname: str,
    *,
    global_settings: Mapping[str, object],
) -> tuple[object, GlobalSettingsOrigin]:
    """The value in effect for the site and the layer it comes from.

    Without an override the site inherits the central value, which in turn falls back
    to the built-in default.
    """
    if varname in site_globals:
        return site_globals[varname], GlobalSettingsOrigin.site

    return effective_value(global_settings, varname)


def save_global_settings_raw(
    vars_: GlobalSettings,
    site_specific: bool = False,
    custom_site_path: str | None = None,
    get_global_settings_config: Callable[[], GlobalConfig] = get_global_config,
    skip_cse_edition_check: bool = False,
) -> None:
    """Writes the settings without letting the configuration domains validate them."""
    if not skip_cse_edition_check and edition(paths.omd_root) is Edition.CLOUD:
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

    per_domain: dict[str, dict[str, object]] = {}
    # TODO: Uee _get_global_config_var_names() from domain class?
    for config_variable in config_variable_registry.values():
        domain = config_variable.primary_domain()
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


def save_global_settings(settings: GlobalSettings, sites: SiteConfigurations) -> None:
    """The entry point for saving the global settings after a user manipulated them."""
    defaults = ABCConfigDomain.get_all_default_globals()
    site_globals = _site_globals_of(sites)
    with _settings_change(
        sites,
        before=finalize_all_settings_per_site(
            defaults, load_configuration_settings(), site_globals
        ),
        after=finalize_all_settings_per_site(defaults, settings, site_globals),
    ):
        save_global_settings_raw(settings)


def _site_globals_of(sites: SiteConfigurations) -> Mapping[SiteId, GlobalSettings]:
    return {site_id: site.get("globals", {}) for site_id, site in sites.items()}


@contextmanager
def _settings_change(
    sites: SiteConfigurations,
    before: Mapping[SiteId, GlobalSettings],
    after: Mapping[SiteId, GlobalSettings],
) -> Iterator[None]:
    """Let every config domain wrap the write of a settings change.

    See ABCConfigDomain.settings_change.
    """
    with ExitStack() as stack:
        for domain in ABCConfigDomain.enabled_domains():
            stack.enter_context(domain.settings_change(sites, before, after))
        yield


def site_global_settings_change(
    sites: SiteConfigurations, site_id: SiteId, site_globals: GlobalSettings
) -> AbstractContextManager[None]:
    """Wraps the write of the overrides a site is about to get.

    See ABCConfigDomain.settings_change.
    """
    defaults = ABCConfigDomain.get_all_default_globals()
    global_settings = load_configuration_settings()
    site_globals_before = _site_globals_of(sites)
    return _settings_change(
        sites,
        before=finalize_all_settings_per_site(defaults, global_settings, site_globals_before),
        after=finalize_all_settings_per_site(
            defaults, global_settings, {**site_globals_before, site_id: site_globals}
        ),
    )


def load_site_global_settings(custom_site_path: str | None = None) -> GlobalSettings:
    return load_configuration_settings(site_specific=True, custom_site_path=custom_site_path)


def save_site_global_settings_raw(
    settings: GlobalSettings, custom_site_path: str | None = None
) -> None:
    save_global_settings_raw(settings, site_specific=True, custom_site_path=custom_site_path)


def make_pending_changes(
    *,
    activation_sites: SiteConfigurations,
    local_site: SiteId,
    acting_user: UserId | None,
    use_git: bool,
) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites,
        local_site=local_site,
        acting_user=acting_user,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=use_git),
            sidebar_reload_change_hook,
            index_update_change_hook,
        ),
    )


def add_global_settings_change(
    config_variable: ConfigVariable,
    *,
    text: LogMessage,
    sites: Sequence[SiteId] | None,
    pending_changes: PendingChanges,
    diff_text: str | None = None,
) -> None:
    pending_changes.add(
        Change(
            action_name="edit-configvar",
            text=text,
            diff_text=diff_text,
            force_restart=config_variable.need_restart(),
            force_apache_reload=config_variable.need_apache_reload(),
            domains=[d.ident() for d in config_variable.all_domains()],
            domain_settings={
                d.ident(): {"need_apache_reload": config_variable.need_apache_reload()}
                for d in config_variable.all_domains()
            },
        ),
        ChangeScope.all_activation_sites() if sites is None else ChangeScope.sites(sites),
    )


def make_global_settings_context(
    edition: Edition,
    target_site_id: SiteId,
    *,
    sites: SiteConfigurations,
    graph_timeranges: Sequence[GraphTimerange],
) -> GlobalSettingsContext:
    return GlobalSettingsContext(
        target_site_id=target_site_id,
        edition_of_local_site=edition,
        site_neutral_log_dir=site_neutral_path(log_dir),
        site_neutral_var_dir=site_neutral_path(var_dir),
        configured_sites=sites,
        configured_graph_timeranges=graph_timeranges,
    )


def is_available_in_global_settings(
    config_variable: ConfigVariable,
    *,
    default_values: Mapping[str, object],
    is_activated: Callable[[str], bool],
) -> bool:
    """Whether this site offers the variable for editing, on whichever settings page.

    A variable without a factory default is unknown to this installation. is_activated is
    the edition-specific activation check for a variable name.
    """
    varname = config_variable.ident()
    return (
        config_variable.in_global_settings()
        and config_variable.primary_domain().enabled()
        and varname in default_values
        and is_activated(varname)
    )


def _masked_value_for_log(
    config_variable: ConfigVariable, context: GlobalSettingsContext, value: object
) -> object:
    visitor = get_visitor(
        config_variable.value_model(context),
        VisitorOptions(migrate_values=True, mask_values=True),
    )
    return visitor.to_disk(RawDiskData(value))


def global_settings_diff_text(
    config_variable: ConfigVariable,
    context: GlobalSettingsContext,
    old_settings: GlobalSettings,
    new_settings: GlobalSettings,
) -> str:
    old_masked = {
        varname: _masked_value_for_log(config_variable, context, value)
        for varname, value in old_settings.items()
    }
    new_masked = {
        varname: _masked_value_for_log(config_variable, context, value)
        for varname, value in new_settings.items()
    }

    unmasked_diff = make_diff(old_settings, new_settings)
    masked_diff = make_diff(old_masked, new_masked)

    if unmasked_diff == masked_diff:
        return make_diff_text(old_masked, new_masked)

    return (masked_diff + "\n" if masked_diff else "") + _("Redacted secrets changed.")
