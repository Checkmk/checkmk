#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Collection, Mapping, Protocol, Sequence

from cmk.utils.rulesets.definition import RuleGroupType

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.table import Foldable, Table, table_element
from cmk.gui.type_defs import ActionResult, HTTPVariables, Icon, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link
from cmk.gui.valuespec import Dictionary, DictionaryEntry, FixedValue, RuleComment, TextInput
from cmk.gui.wato._main_module_topics import MainModuleTopicQuickSetup
from cmk.gui.wato.pages.hosts import ModeEditHost
from cmk.gui.wato.pages.password_store import ModeEditPassword
from cmk.gui.wato.pages.rulesets import ModeEditRule
from cmk.gui.watolib.configuration_bundles import (
    BUNDLE_DOMAINS,
    BundleId,
    BundleReferences,
    ConfigBundle,
    ConfigBundleStore,
    delete_config_bundle,
    identify_bundle_group_type,
    identify_bundle_references,
    load_group_bundles,
    valid_special_agent_bundle,
)
from cmk.gui.watolib.hosts_and_folders import make_action_link
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.rulespecs import rulespec_registry

from cmk.ccc.exceptions import MKGeneralException


def register(main_module_registry: MainModuleRegistry, mode_registry: ModeRegistry) -> None:
    # main_module_registry.register(MainModuleQuickSetupAWS)    # TODO: register once quick setup is implemented
    mode_registry.register(ModeConfigurationBundle)
    mode_registry.register(ModeEditConfigurationBundles)


class ModeEditConfigurationBundles(WatoMode):
    VAR_NAME = "varname"
    VAR_ACTION = "_action"
    VAR_BUNDLE_ID = "_bundle_id"

    @classmethod
    def name(cls) -> str:
        return "edit_configuration_bundles"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def ensure_permissions(self) -> None:
        self._ensure_static_permissions()
        for domain_definition in BUNDLE_DOMAINS[self._bundle_group_type]:
            pname = domain_definition.permission
            user.need_permission(pname if "." in pname else ("wato." + pname))

    def _from_vars(self) -> None:
        self._name = request.get_ascii_input_mandatory(self.VAR_NAME)
        self._bundle_group_type = identify_bundle_group_type(self._name)
        if self._bundle_group_type not in BUNDLE_DOMAINS:
            raise MKUserError(
                None,
                _("No edit configuration bundle implemented for bundle group type '%s'.")
                % self._name,
            )

    def _breadcrumb_url(self) -> str:
        return self.mode_url(varname=self._name)

    def title(self) -> str:
        if self._bundle_group_type is RuleGroupType.SPECIAL_AGENTS:
            title = rulespec_registry[self._name].title
            assert title is not None
            return title
        raise MKGeneralException("Not implemented bundle group type")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="configurations",
                    title=_("Configurations"),
                    topics=[
                        PageMenuTopic(
                            title=_("Configurations"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add configuration"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        ""
                                    ),  # TODO: add Quick setup creation page
                                    is_shortcut=True,
                                    is_suggested=True,
                                )
                            ],
                        )
                    ],
                )
            ],
            breadcrumb=breadcrumb,
        )
        return menu

    def page(self) -> None:
        if not active_config.wato_hide_varnames:
            display_varname = (
                '%s["%s"]' % tuple(self._name.split(":")) if ":" in self._name else self._name
            )
            html.div(display_varname, class_="varname")

        self._bundles_listing(self._name)

    def _bundles_listing(self, group_name: str) -> None:
        bundle_ids = set(load_group_bundles(group_name).keys())
        if not bundle_ids:
            # TODO (CMK-18347): add redesigned overview for empty configurations
            html.div(_("No configuration yet"))
            return

        bundles_with_references = identify_bundle_references(group_name, bundle_ids)
        if self._bundle_group_type is RuleGroupType.SPECIAL_AGENTS:
            self._special_agent_bundles_listing(group_name, bundles_with_references)
            return

        raise MKGeneralException("Not implemented")

    def _action_url(self, action: str, bundle_id: BundleId) -> str:
        vars_: HTTPVariables = [
            ("mode", request.var("mode", self.name())),
            (self.VAR_NAME, self._name),
            (self.VAR_BUNDLE_ID, bundle_id),
            (self.VAR_ACTION, action),
        ]
        return make_action_link(vars_)

    def action(self) -> ActionResult:
        check_csrf_token()
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        action = request.get_ascii_input_mandatory(self.VAR_ACTION)
        bundle_id = BundleId(request.get_ascii_input_mandatory(self.VAR_BUNDLE_ID))
        if action == "delete":
            delete_config_bundle(bundle_id)

        return redirect(self.mode_url())

    def _special_agent_bundles_listing(
        self, group_name: str, bundles: Mapping[BundleId, BundleReferences]
    ) -> None:
        special_agent_valuespec = rulespec_registry[group_name].valuespec
        with table_element(
            table_id=None,
            title="Configurations",
            searchable=False,
            sortable=False,
            limit=None,
            foldable=Foldable.FOLDABLE_SAVE_STATE,
            omit_update_header=True,
        ) as table:
            for index, (bundle_id, bundle) in enumerate(sorted(bundles.items())):
                if not valid_special_agent_bundle(bundle):
                    raise MKGeneralException(f"Invalid configuration: {bundle_id}")
                assert bundle.rules is not None
                assert bundle.hosts is not None
                rule_value = bundle.rules[0].value
                host_name = bundle.hosts[0].name()
                table.row()

                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(index + 1)

                self._show_bundle_icons(table, bundle_id)

                table.cell("Name", css=[])
                html.write_text_permissive(bundle_id)

                table.cell(_("Value"), css=["value"])

                # We use the same table layout for the host name to have the same format as for
                # the rule rendering
                html.write_text_permissive(
                    HTMLWriter.render_table(
                        HTMLWriter.render_tr(
                            HTMLWriter.render_td("Host name:", class_="title")
                            + HTMLWriter.render_td(host_name)
                        )
                    )
                )
                try:
                    value_html = special_agent_valuespec.value_to_html(rule_value)
                except Exception as e:
                    try:
                        reason = str(e)
                        special_agent_valuespec.validate_datatype(rule_value, "")
                    except Exception as e2:
                        reason = str(e2)

                    value_html = (
                        html.render_icon("alert")
                        + HTML.with_escaping(_("The value of this rule is not valid. "))
                        + escape_to_html_permissive(reason)
                    )
                html.write_text_permissive(value_html)

    def _show_bundle_icons(self, table: Table, bundle_id: BundleId) -> None:
        table.cell("", css=["buttons"])
        html.empty_icon()

        table.cell(_("Actions"), css=["buttons rulebuttons"])
        edit_url = ""  # TODO: introduce edit button
        html.icon_button(url=edit_url, title=_("Edit this configuration"), icon="edit")

        html.icon_button(
            url=make_confirm_delete_link(
                url=self._action_url("delete", bundle_id),
                title=_("Delete configuration %s") % bundle_id,
            ),
            title=_("Delete this configuration"),
            icon="delete",
        )


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
