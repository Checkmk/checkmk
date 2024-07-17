#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Collection, Sequence
from typing import Protocol

from cmk.utils.rulesets.definition import RuleGroupType

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Icon, PermissionName
from cmk.gui.valuespec import Dictionary, DictionaryEntry, FixedValue, RuleComment, TextInput
from cmk.gui.wato._main_module_topics import MainModuleTopicQuickSetup
from cmk.gui.wato.pages.hosts import ModeEditHost
from cmk.gui.wato.pages.password_store import ModeEditPassword
from cmk.gui.wato.pages.rulesets import ModeEditRule
from cmk.gui.watolib.configuration_bundles import (
    BUNDLE_DOMAINS,
    BundleId,
    ConfigBundle,
    ConfigBundleStore,
    identify_bundle_references,
)
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic
from cmk.gui.watolib.mode import ModeRegistry, WatoMode


def register(main_module_registry: MainModuleRegistry, mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeConfigurationBundle)


class MainModuleQuickSetupAWS(ABCMainModule):
    @property
    def mode_or_url(self) -> str:
        return "quick_setup_aws"

    @property
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicQuickSetup

    @property
    def title(self) -> str:
        return _("Amazon Web Service (AWS)")

    @property
    def icon(self) -> Icon:
        return "quick_setup_aws"

    @property
    def permission(self) -> None | str:
        return None

    @property
    def description(self) -> str:
        return _("Configure Amazon Web Service (AWS) monitoring in Checkmk")

    @property
    def sort_index(self) -> int:
        return 10

    @property
    def is_show_more(self) -> bool:
        return False

    @classmethod
    def megamenu_search_terms(cls) -> Sequence[str]:
        return ["aws"]


class EditDCDConnection(Protocol):
    def __init__(self) -> None: ...

    def from_vars(self, ident_var: str) -> None: ...

    def page(self, form_name: str) -> None: ...


class ModeConfigurationBundle(WatoMode):
    edit_dcd_connection_hook: Callable[[], EditDCDConnection | None] = lambda: None

    @classmethod
    def name(cls) -> str:
        return "edit_configuration_bundle"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def ensure_permissions(self) -> None:
        self._ensure_static_permissions()
        for domain_definition in BUNDLE_DOMAINS.get(self._rule_group_type, []):
            pname = domain_definition.permission
            user.need_permission(pname if "." in pname else ("wato." + pname))

    def title(self) -> str:
        return _("Edit configuration: %s") % self._bundle["title"]

    def _from_vars(self) -> None:
        self._bundle_id = request.get_validated_type_input_mandatory(BundleId, "bundle_id")
        bundle_store = ConfigBundleStore().load_for_reading()
        if self._bundle_id not in bundle_store:
            raise MKUserError(
                "bundle_id",
                _('The configuration "%s" does not exist.') % self._bundle_id,
            )
        self._bundle: ConfigBundle = bundle_store[self._bundle_id]
        self._bundle_group = self._bundle["group"]
        self._bundle_references = identify_bundle_references(self._bundle_group, {self._bundle_id})[
            self._bundle_id
        ]

        self._rule_group_type = RuleGroupType(self._bundle_group.split(":")[0])
        match self._rule_group_type:
            case RuleGroupType.SPECIAL_AGENTS:
                self._special_agents_from_vars()
            case _:
                raise MKUserError(
                    None,
                    _("No edit configuration bundle implemented for bundle group type '%s'.")
                    % self._bundle_group,
                )

    def _special_agents_from_vars(self) -> None:
        if not all(
            [
                self._bundle_references.rules,
                self._bundle_references.hosts,
                self._bundle_references.passwords,
            ]
        ):
            raise MKUserError(
                None,
                _("The configuration bundle does not contain all required objects."),
            )

        assert self._bundle_references.rules
        assert len(self._bundle_references.rules) == 1
        assert self._bundle_references.hosts
        assert len(self._bundle_references.hosts) == 1
        assert self._bundle_references.passwords

        # Rule
        ModeEditRule.set_vars(self._bundle_group, self._bundle_references.rules[0].id)
        self._edit_rule = ModeEditRule()

        # Host
        ModeEditHost.set_vars(self._bundle_references.hosts[0].name())
        self._edit_host = ModeEditHost()

        # DCD connections
        if self._bundle_references.dcd_connections:
            for index, dcd_connection in enumerate(self._bundle_references.dcd_connections):
                request.set_var(f"dcd_id_{index}", dcd_connection[0])

            self._edit_dcd_connections: Sequence[EditDCDConnection | None] = [
                self.edit_dcd_connection_hook() for _dcd in self._bundle_references.dcd_connections
            ]
            for index, edit_dcd_connection in enumerate(self._edit_dcd_connections):
                if edit_dcd_connection:
                    edit_dcd_connection.from_vars(f"dcd_id_{index}")

        # Passwords
        for index, password in enumerate(self._bundle_references.passwords):
            request.set_var(f"password_id_{index}", password[0])
        self._edit_passwords = [ModeEditPassword() for _pw in self._bundle_references.passwords]
        for index, edit_password in enumerate(self._edit_passwords):
            edit_password.from_vars(f"password_id_{index}")

    @staticmethod
    def _configuration_vs(bundle_id: str) -> Dictionary:
        elements: Sequence[DictionaryEntry] = [
            ("_name", TextInput(title=_("Name"), size=80)),
            ("_comment", RuleComment()),
            ("_bundle_id", FixedValue(title=_("Configuration bundle ID"), value=bundle_id)),
        ]
        return Dictionary(
            title=_("Configuration bundle properties"),
            optional_keys=False,
            render="form",
            elements=elements,
        )

    def _sub_page_configuration(self) -> None:
        html.h1(_("Configuration"), class_=["edit_configuration_bundle_header"])
        with html.form_context("edit_bundle", method="POST"):
            self._configuration_vs(self._bundle_id).render_input(
                "options",
                {
                    "_name": self._bundle["title"],
                    "_comment": self._bundle["comment"],
                },
            )

    def _sub_page_rule(self) -> None:
        html.h1(_("Rule"), class_=["edit_configuration_bundle_header"])
        self._edit_rule.page()

    def _sub_page_host(self) -> None:
        html.h1(_("Host"), class_=["edit_configuration_bundle_header"])
        self._edit_host.page()

    def _sub_page_dcd_connection(self) -> None:
        if any(edit_dcd_connection for edit_dcd_connection in self._edit_dcd_connections):
            html.h1(_("Dynamic host management"), class_=["edit_configuration_bundle_header"])
            for index, edit_dcd_connection in enumerate(self._edit_dcd_connections):
                if edit_dcd_connection:
                    edit_dcd_connection.page(f"edit_dcd_{index}")

    def _sub_page_password(self) -> None:
        if self._edit_passwords:
            html.h1(_("Password"), class_=["edit_configuration_bundle_header"])
            for index, edit_password in enumerate(self._edit_passwords):
                edit_password.page(f"edit_password_{index}")

    def page(self) -> None:
        match self._rule_group_type:
            case RuleGroupType.SPECIAL_AGENTS:
                self._sub_page_configuration()
                self._sub_page_rule()
                self._sub_page_host()
                self._sub_page_dcd_connection()
                self._sub_page_password()
            case _:
                raise MKUserError(
                    None,
                    _("No edit configuration bundle implemented for bundle group type '%s'.")
                    % self._bundle_group,
                )
