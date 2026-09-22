#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module-near curated settings pages for Checkmk Maps.

The same admin settings that Setup → Global settings exposes per-variable are
*also* reachable right next to the module (Customize → Maps → the "Maps" page
menu), grouped into two curated forms — the DCD pattern
(``dcd_global_settings``): same variables, same form specs, two entry points.

All Maps settings live in the feature's own :class:`ConfigDomainMaps`
(``maps.d/wato/global.mk``), so both forms persist to the same file; each writes
its own keys, merged over the current content so the other form's keys survive.

That file has a second writer — Setup → Global settings, through the
``ConfigVariable``s of :mod:`cmk.maps.gui._config_variables`. The two interleave
safely and in both directions: :class:`WatoMultiConfigFile` and
:meth:`ABCConfigDomain.save` use the same ``<varname> = <repr>`` format, this mode
merges over the file's current content, and WATO's own save round-trips the whole
domain (it re-saves what ``load_configuration_settings`` just read). Like DCD's
``dcd_global_settings``, the curated forms show the *central* values only —
per-site overrides (``sitespecific.mk``) stay with the standard global-settings
UI that owns them.

The two forms split the settings along the "read by the daemon?" seam:

- :class:`ModeMapsAuthoringSettings` — map/object authoring defaults (GUI-only,
  never read by the daemon).
- :class:`ModeMapsDaemonSettings` — connections + the runtime knobs (read +
  replicated to the daemon).

Both are WATO modes (served by ``wato.py``), so editing them is a Setup action
(``wato.use``/``wato.edit``) gated additionally by ``maps.configure`` — global
defaults are an admin concern regardless of the seam. Unlike DCD we record the
change *without* ``force_restart``: :class:`ConfigDomainMaps` re-reads its config
dir per request (``needs_activation = False``), so shipping the file via the
domain's ReplicationPath on Activate Changes is enough.
"""

from collections.abc import Collection
from typing import NotRequired, override, TypedDict

from cmk.ccc.site import omd_site
from cmk.ccc.version import Edition
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.pages import PageContext
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.type_defs import ActionResult
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook
from cmk.gui.watolib.simple_config_file import WatoMultiConfigFile
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_LOG_LEVEL,
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    CONFIG_VAR_STATE_REFRESH_INTERVAL,
    ConfigDomainMaps,
)
from cmk.maps.gui._config_variables import (
    connections_form_spec,
    log_level_form_spec,
    map_defaults_form_spec,
    object_defaults_form_spec,
    state_refresh_interval_form_spec,
)
from cmk.maps.gui._permissions import PERMISSION_SECTION_MAPS
from cmk.shared_typing.main_menu import NavItem
from cmk.web.utils.csrf_token import check_csrf_token
from cmk.web.utils.permission_verification import PermissionName

# The page that mounts the SPA (Customize → Maps); the settings modes root their
# breadcrumb here and cancel/return to it.
_MAPS_HOME_URL = "maps.py"
# Editing Maps globals is an admin concern regardless of the map/daemon seam.
_MAPS_CONFIGURE_PERMISSION: PermissionName = f"{PERMISSION_SECTION_MAPS.name}.configure"


# The keys ARE the config-variable idents (the GUI↔daemon .mk contract). Values
# stay loosely typed: the value specs already validate structure on submit; this
# TypedDict only pins the shape WATO persists to ``global.mk``. Both curated forms
# share this one file (all Maps settings live in the maps.d domain), so each save
# merges its keys over the current content — see ``_ABCMapsSettingsMode.action``.
class MapsConfig(TypedDict):
    maps_connections: NotRequired[list[dict[str, object]]]
    maps_log_level: NotRequired[str]
    maps_state_refresh_interval: NotRequired[int]
    maps_map_defaults: NotRequired[dict[str, object]]
    maps_object_defaults: NotRequired[dict[str, object]]


class MapsConfigFile(WatoMultiConfigFile[MapsConfig]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=ConfigDomainMaps().config_dir() / "global.mk",
            spec_class=MapsConfig,
            load_default=MapsConfig,
        )


class _ABCMapsSettingsMode(WatoMode[None]):
    """Shared plumbing for the two curated Maps settings forms.

    Subclasses supply only the form name and the value spec; everything else
    (breadcrumb under Customize → Maps, the save/cancel page menu, load/render,
    validate/save + Pending Changes) is shared. Both forms read and write the one
    ``maps.d`` ``global.mk`` — the form's value spec selects which keys each edits.
    """

    _form_name: str = "maps_settings"

    def __init__(self, edition: Edition, ctx: PageContext) -> None:
        super().__init__(edition, ctx)
        self._current = MapsConfigFile().load_for_reading()

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return [_MAPS_CONFIGURE_PERMISSION]

    def _valuespec(self) -> Dictionary:
        raise NotImplementedError

    @override
    def main_menu(self) -> NavItem:
        return main_menu_registry.menu_customize()

    @override
    def breadcrumb(self) -> Breadcrumb:
        # Only the levels below the main menu: cmk.gui.wato.page_handler prepends
        # ``make_main_menu_breadcrumb(mode.main_menu())`` itself, and
        # :meth:`main_menu` already roots these modes under Customize rather than
        # Setup (the module has no Setup tile). "Maps" links back to the SPA.
        return Breadcrumb(
            [
                BreadcrumbItem(title=_("Maps"), url=_MAPS_HOME_URL, id="maps"),
                self._breadcrumb_item(),
            ]
        )

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            self.title(),
            breadcrumb,
            form_name=self._form_name,
            button_name="_save",
            add_cancel_link=True,
            cancel_url=_MAPS_HOME_URL,
        )

    @override
    def page(self, config: Config) -> None:
        with html.form_context(self._form_name, method="POST"):
            self._valuespec().render_input(self._form_name, dict(self._current))
            forms.end()
            html.hidden_fields()

    @override
    def action(self, config: Config) -> ActionResult:
        check_csrf_token(session, request, i18n=_)
        if not transactions.check_transaction(request):
            return redirect(_MAPS_HOME_URL)

        value_spec = self._valuespec()
        table = value_spec.from_html_vars(self._form_name)
        # ``from_html_vars`` only reads the fields back; nothing downstream checks
        # the specs' own constraints — ``validate_and_save`` validates against the
        # config file's TypedDict shape, not against ranges or id patterns. Without
        # this an out-of-range refresh interval or a malformed connection id would
        # reach global.mk and be replicated to the daemon.
        value_spec.validate_datatype(table, self._form_name)
        value_spec.validate_value(table, self._form_name)
        # Both forms share one global.mk; merge this form's keys over the current
        # content so the other form's keys are preserved.
        config_file = MapsConfigFile()
        merged = {**config_file.load_for_reading(), **table}
        config_file.validate_and_save(merged, pprint_value=config.wato_pprint_config)

        PendingChanges(
            activation_sites=activation_sites(config.sites),
            local_site=omd_site(),
            acting_user=user.id,
            store=PendingChangesStore(),
            hooks=(
                make_audit_log_change_hook(use_git=config.wato_use_git),
                sidebar_reload_change_hook,
                index_update_change_hook,
            ),
        ).add(
            Change(
                action_name="maps-settings",
                text=_("Changed Checkmk Maps settings"),
                # No force_restart: the daemon re-reads its config per request;
                # the domain's ReplicationPath ships the file on activation.
                domains=[ConfigDomainMaps().ident()],
            ),
            ChangeScope.all_activation_sites(),
        )
        return redirect(_MAPS_HOME_URL)


class ModeMapsAuthoringSettings(_ABCMapsSettingsMode):
    _form_name = "maps_authoring_settings"

    @classmethod
    @override
    def name(cls) -> str:
        return "maps_authoring_settings"

    @override
    def title(self) -> str:
        return _("Map & object defaults")

    @override
    def _valuespec(self) -> Dictionary:
        return Dictionary(
            render="form",
            optional_keys=False,
            elements=[
                (CONFIG_VAR_MAP_DEFAULTS, convert_to_legacy_valuespec(map_defaults_form_spec(), _)),
                (
                    CONFIG_VAR_OBJECT_DEFAULTS,
                    convert_to_legacy_valuespec(object_defaults_form_spec(), _),
                ),
            ],
        )


class ModeMapsDaemonSettings(_ABCMapsSettingsMode):
    _form_name = "maps_daemon_settings"

    @classmethod
    @override
    def name(cls) -> str:
        return "maps_daemon_settings"

    @override
    def title(self) -> str:
        return _("Connections & daemon")

    @override
    def _valuespec(self) -> Dictionary:
        return Dictionary(
            render="form",
            optional_keys=False,
            elements=[
                (CONFIG_VAR_CONNECTIONS, convert_to_legacy_valuespec(connections_form_spec(), _)),
                (CONFIG_VAR_LOG_LEVEL, convert_to_legacy_valuespec(log_level_form_spec(), _)),
                (
                    CONFIG_VAR_STATE_REFRESH_INTERVAL,
                    convert_to_legacy_valuespec(state_refresh_interval_form_spec(), _),
                ),
            ],
        )


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeMapsAuthoringSettings)
    mode_registry.register(ModeMapsDaemonSettings)
