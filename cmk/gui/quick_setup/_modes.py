#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from collections.abc import Collection, Iterable, Mapping, Sequence
from typing import override, Protocol

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.rulesets.definition import RuleGroup, RuleGroupType

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.page_menu_entry import enable_page_menu_entry
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.table import Foldable, Table, table_element
from cmk.gui.type_defs import ActionResult, HTTPVariables, Icon, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link
from cmk.gui.valuespec import Dictionary, DictionaryEntry, FixedValue, RuleComment, TextInput
from cmk.gui.wato import TileMenuRenderer
from cmk.gui.wato._main_module_topics import MainModuleTopicQuickSetup
from cmk.gui.wato.pages.hosts import ModeEditHost
from cmk.gui.wato.pages.password_store import ModeEditPassword
from cmk.gui.wato.pages.rulesets import ModeEditRule
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.configuration_bundle_store import (
    BundleId,
    ConfigBundle,
    ConfigBundleStore,
    load_group_bundles,
)
from cmk.gui.watolib.configuration_bundles import (
    bundle_domains,
    BundleReferences,
    delete_config_bundle,
    delete_config_bundle_objects,
    edit_config_bundle_configuration,
    identify_bundle_references,
    valid_special_agent_bundle,
)
from cmk.gui.watolib.hosts_and_folders import make_action_link
from cmk.gui.watolib.main_menu import ABCMainModule, MainModuleRegistry, MainModuleTopic, MenuItem
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.rulespecs import rulespec_registry


def register(main_module_registry: MainModuleRegistry, mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeConfigurationBundle)
    mode_registry.register(ModeEditConfigurationBundles)
    mode_registry.register(ModeQuickSetupSpecialAgent)
    main_module_registry.register(MainModuleQuickSetupAWS)
    main_module_registry.register(MainModuleQuickSetupAzure)
    main_module_registry.register(MainModuleQuickSetupGCP)


class ModeQuickSetupSpecialAgent(WatoMode):
    """
    This mode allows to create a new special agent configuration using the quick setup. It
    is solely restricted to special agent based rules and relies on the RuleGroup.SpecialAgents
    naming convention of the rulespec entry
    """

    VAR_NAME = "varname"

    @classmethod
    @override
    def name(cls) -> str:
        return "new_special_agent_configuration"

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditConfigurationBundles

    @override
    def _breadcrumb_url(self) -> str:
        return self.mode_url(varname=self._name)

    @override
    def _from_vars(self) -> None:
        self._name = request.get_ascii_input_mandatory(self.VAR_NAME)
        if not self._name.startswith(RuleGroupType.SPECIAL_AGENTS.value):
            raise MKUserError(
                None,
                _("Add configuration is only available for special agent based rules."),
            )

        quick_setup = quick_setup_registry.get(self._name)
        if quick_setup is None:
            raise MKUserError(None, _("No Configuration Quick setup for %s available") % self._name)
        self._quick_setup_id = quick_setup.id

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return []

    @override
    def ensure_permissions(self) -> None:
        self._ensure_static_permissions()
        for domain_definition in bundle_domains()[RuleGroupType.SPECIAL_AGENTS]:
            pname = domain_definition.permission
            user.need_permission(pname if "." in pname else ("wato." + pname))

    @override
    def title(self) -> str:
        title = rulespec_registry[self._name].title
        assert title is not None
        return _("Add %s configuration") % title

    @override
    def breadcrumb(self) -> Breadcrumb:
        with request.stashed_vars():
            return super().breadcrumb()

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            title=_("Configuration"),
            breadcrumb=breadcrumb,
            add_cancel_link=True,
            cancel_url=mode_url(mode_name=ModeEditConfigurationBundles.name(), varname=self._name),
        )

    @override
    def page(self) -> None:
        enable_page_menu_entry(html, "inline_help")
        html.vue_component(
            component_name="cmk-quick-setup",
            data={
                "quick_setup_id": self._quick_setup_id,
                "mode": "guided",
                "toggle_enabled": False,
            },
        )


class ModeEditConfigurationBundles(WatoMode):
    VAR_NAME = "varname"
    VAR_ACTION = "_action"
    VAR_BUNDLE_ID = "_bundle_id"

    @classmethod
    @override
    def name(cls) -> str:
        return "edit_configuration_bundles"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return []

    @override
    def _topic_breadcrumb_item(self) -> Iterable[BreadcrumbItem]:
        """Return the BreadcrumbItem for the topic of this mode"""
        yield BreadcrumbItem(
            title=MainModuleTopicQuickSetup.title,
            url=None,
        )

    @override
    def ensure_permissions(self) -> None:
        self._ensure_static_permissions()
        for domain_definition in bundle_domains()[self._bundle_group_type]:
            pname = domain_definition.permission
            user.need_permission(pname if "." in pname else ("wato." + pname))

    @override
    def _from_vars(self) -> None:
        self._name = request.get_ascii_input_mandatory(self.VAR_NAME)
        try:
            self._bundle_group_type = RuleGroupType(self._name.split(":")[0])
        except ValueError:
            raise MKUserError(None, _("Invalid configuration bundle group type."))
        if self._bundle_group_type not in bundle_domains():
            raise MKUserError(
                self.VAR_NAME,
                _("No edit configuration bundle implemented for bundle group type '%s'.")
                % self._name,
            )

    @override
    def _breadcrumb_url(self) -> str:
        return self.mode_url(varname=self._name)

    @override
    def title(self) -> str:
        if self._bundle_group_type is RuleGroupType.SPECIAL_AGENTS:
            title = rulespec_registry[self._name].title
            assert title is not None
            return title
        raise MKGeneralException("Not implemented bundle group type")

    @override
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
                                        mode_url(
                                            ModeQuickSetupSpecialAgent.name(),
                                            varname=self._name,
                                        )
                                    ),
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

    @override
    def page(self) -> None:
        if not active_config.wato_hide_varnames:
            display_varname = (
                '%s["%s"]' % tuple(self._name.split(":")) if ":" in self._name else self._name
            )
            html.div(display_varname, class_="varname")

        self._bundles_listing(self._name)

    def _delete_bundle(self, bundle_id: BundleId) -> None:
        if self._bundle_group_type is RuleGroupType.SPECIAL_AGENTS:
            # revert changes does not work correctly when a config sync to another site occurred
            # for consistency reasons we always prevent the user from reverting the changes
            prevent_discard_changes = True
        else:
            raise MKGeneralException("Not implemented")

        delete_config_bundle(
            bundle_id,
            user_id=user.id,
            pprint_value=active_config.wato_pprint_config,
            use_git=active_config.wato_use_git,
            debug=active_config.debug,
        )
        add_change(
            action_name="delete-quick-setup",
            text=_("Deleted Quick setup {bundle_id}").format(bundle_id=bundle_id),
            user_id=user.id,
            prevent_discard_changes=prevent_discard_changes,
            use_git=active_config.wato_use_git,
        )

    def _bundles_listing(self, group_name: str) -> None:
        bundle_ids = set(load_group_bundles(group_name).keys())
        if not bundle_ids:
            self._no_bundles()
            return

        bundles_with_references = identify_bundle_references(group_name, bundle_ids)
        if self._bundle_group_type is RuleGroupType.SPECIAL_AGENTS:
            self._special_agent_bundles_listing(group_name, bundles_with_references)
            return

        raise MKGeneralException("Not implemented")

    def _no_bundles(self) -> None:
        if self._bundle_group_type is RuleGroupType.SPECIAL_AGENTS:
            subtype = self._name.split(":", maxsplit=1)[1]
            html.div(
                html.render_icon(f"qs_{subtype}")
                + html.render_b(_("No %s configuration yet") % self.title())
                + html.render_p(
                    _(
                        'Click the "Add configuration" button to start setting up your first '
                        "configuration."
                    )
                )
                + html.render_a(
                    _("Add configuration"),
                    mode_url(ModeQuickSetupSpecialAgent.name(), varname=self._name),
                ),
                css=["no-config-bundles"],
            )
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

    @override
    def action(self) -> ActionResult:
        check_csrf_token()
        if not transactions.check_transaction():
            return redirect(self.mode_url(**{"mode": self.name(), self.VAR_NAME: self._name}))

        bundle_id = BundleId(request.get_ascii_input_mandatory(self.VAR_BUNDLE_ID))
        action = request.get_ascii_input_mandatory(self.VAR_ACTION)
        if action == "delete":
            self._delete_bundle(bundle_id)

        return redirect(self.mode_url(**{"mode": self.name(), self.VAR_NAME: self._name}))

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
        edit_url = mode_url(ModeConfigurationBundle.name(), bundle_id=bundle_id)
        html.icon_button(url=edit_url, title=_("Edit this configuration"), icon="edit")

        html.icon_button(
            url=make_confirm_delete_link(
                url=self._action_url("delete", bundle_id),
                title=_("Delete configuration %s") % bundle_id,
            ),
            title=_("Delete this configuration"),
            icon="delete",
        )


class ABCMainModuleQuickSetup(ABCMainModule, ABC):
    @property
    @override
    def topic(self) -> MainModuleTopic:
        return MainModuleTopicQuickSetup

    @property
    @override
    def permission(self) -> None | str:
        # this should've only been used within `may_see`, which we've overridden...
        raise NotImplementedError()

    @override
    def may_see(self) -> bool:
        domains = bundle_domains()
        if self.rule_group_type not in domains:
            return False

        for domain_definition in domains[self.rule_group_type]:
            permission: str = domain_definition.permission
            permission = permission if "." in permission else ("wato." + permission)
            if not user.may(permission):
                return False

        return True

    @property
    @override
    def is_show_more(self) -> bool:
        return False

    @property
    @abstractmethod
    def rule_group_type(self) -> RuleGroupType:
        pass


class MainModuleQuickSetupAWS(ABCMainModuleQuickSetup):
    @property
    @override
    def rule_group_type(self) -> RuleGroupType:
        return RuleGroupType.SPECIAL_AGENTS

    @property
    @override
    def mode_or_url(self) -> str:
        return mode_url(ModeEditConfigurationBundles.name(), varname=RuleGroup.SpecialAgents("aws"))

    @property
    @override
    def title(self) -> str:
        return _("Amazon Web Service (AWS)")

    @property
    @override
    def icon(self) -> Icon:
        return "quick_setup_aws"

    @property
    @override
    def description(self) -> str:
        return _("Configure Amazon Web Service (AWS) monitoring in Checkmk")

    @property
    @override
    def sort_index(self) -> int:
        return 10

    @classmethod
    @override
    def main_menu_search_terms(cls) -> Sequence[str]:
        return ["aws"]


class MainModuleQuickSetupAzure(ABCMainModuleQuickSetup):
    @property
    @override
    def rule_group_type(self) -> RuleGroupType:
        return RuleGroupType.SPECIAL_AGENTS

    @property
    @override
    def mode_or_url(self) -> str:
        return mode_url(
            ModeEditConfigurationBundles.name(),
            varname=RuleGroup.SpecialAgents("azure"),
        )

    @property
    @override
    def title(self) -> str:
        return _("Microsoft Azure")

    @property
    @override
    def icon(self) -> Icon:
        return "azure_vms"

    @property
    @override
    def description(self) -> str:
        return _("Configure Microsoft Azure monitoring in Checkmk")

    @property
    @override
    def sort_index(self) -> int:
        return 11

    @classmethod
    @override
    def main_menu_search_terms(cls) -> Sequence[str]:
        return ["azure"]


class MainModuleQuickSetupGCP(ABCMainModuleQuickSetup):
    @property
    @override
    def rule_group_type(self) -> RuleGroupType:
        return RuleGroupType.SPECIAL_AGENTS

    @property
    @override
    def mode_or_url(self) -> str:
        return mode_url(
            ModeEditConfigurationBundles.name(),
            varname=RuleGroup.SpecialAgents("gcp"),
        )

    @property
    @override
    def title(self) -> str:
        return _("Google Cloud Platform (GCP)")

    @property
    @override
    def icon(self) -> Icon:
        return "gcp"

    @property
    @override
    def description(self) -> str:
        return _("Configure Google Cloud Platform (GCP) monitoring in Checkmk")

    @property
    @override
    def sort_index(self) -> int:
        return 12

    @classmethod
    @override
    def main_menu_search_terms(cls) -> Sequence[str]:
        return ["gcp"]


class EditDCDConnection(Protocol):
    def __init__(self) -> None: ...

    def from_vars(self, ident_var: str) -> None: ...

    def page(self, form_name: str) -> None: ...

    def action(self) -> ActionResult: ...


class ModeConfigurationBundle(WatoMode):
    FORM_PREFIX = "options"
    VAR_ACTION = "action"

    @classmethod
    @override
    def name(cls) -> str:
        return "edit_configuration_bundle"

    @classmethod
    @override
    def parent_mode(cls) -> type["WatoMode"]:
        return ModeEditConfigurationBundles

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return []

    @override
    def ensure_permissions(self) -> None:
        if not self._existing_bundle:
            return

        self._ensure_static_permissions()
        for domain_definition in bundle_domains().get(self._rule_group_type, []):
            pname = domain_definition.permission
            user.need_permission(pname if "." in pname else ("wato." + pname))

    @override
    def title(self) -> str:
        if not self._existing_bundle:
            return _("Configuration: %s") % self._bundle_id
        return _("Edit configuration: %s") % self._bundle["title"]

    @override
    def breadcrumb(self) -> Breadcrumb:
        if not self._existing_bundle:
            return Breadcrumb()

        request.set_var(ModeEditConfigurationBundles.VAR_NAME, self._bundle_group)
        return super().breadcrumb()

    @override
    def _from_vars(self) -> None:
        self._bundle_id = request.get_validated_type_input_mandatory(BundleId, "bundle_id")

        bundle_store = ConfigBundleStore().load_for_reading()
        self._existing_bundle = True
        if self._bundle_id not in bundle_store:
            self._existing_bundle = False
            return

        self._bundle: ConfigBundle = bundle_store[self._bundle_id]
        self._bundle_group = self._bundle["group"]
        self._bundle_references = identify_bundle_references(self._bundle_group, {self._bundle_id})[
            self._bundle_id
        ]

        self._rule_group_type = RuleGroupType(self._bundle_group.split(":")[0])
        match self._rule_group_type:
            case RuleGroupType.SPECIAL_AGENTS:
                self._verify_special_agent_vars()
            case _:
                raise MKUserError(
                    None,
                    _("No edit configuration bundle implemented for bundle group type '%s'.")
                    % self._bundle_group,
                )

    def _verify_special_agent_vars(self) -> None:
        if not valid_special_agent_bundle(self._bundle_references):
            raise MKGeneralException(
                _(
                    "The configuration bundle '%s' is not valid. "
                    "This likely means that parts of it were removed or not properly created."
                )
                % self._bundle_id,
            )

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Actions"), breadcrumb, form_name="edit_bundle", button_name="_save"
        )

    @override
    def page(self) -> None:
        if not self._existing_bundle:
            html.open_div(class_="really")
            html.h3(_("The configuration bundle %s does not exist") % self._bundle_id)
            html.br()
            html.write_text_permissive(
                _(
                    "This can happen if the configuration bundle was deleted and some underlying "
                    "objects were not properly cleaned up. By pressing the button 'Clean Up' you "
                    "can remove all objects that reference the non-existing configuration."
                )
            )
            html.br()
            with html.form_context("edit_bundle", method="POST"):
                html.button("_clean_up", _("Clean Up"), "")
                html.hidden_fields(add_action_vars=True)

            html.close_div()
            return

        html.h1(_("Configuration"), class_=["edit_configuration_bundle_header"])
        match self._rule_group_type:
            case RuleGroupType.SPECIAL_AGENTS:
                self._page_section_bundle_links()
                self._page_section_bundle_configuration()
            case _:
                raise MKUserError(
                    None,
                    _("No edit configuration bundle implemented for bundle group type '%s'.")
                    % self._bundle_group,
                )

    def _page_section_bundle_links(self) -> None:
        assert self._bundle_references.rules and self._bundle_references.hosts
        host = self._bundle_references.hosts[0]
        rule = self._bundle_references.rules[0]

        bundle_entity_links = [
            MenuItem(
                mode_or_url=ModeEditRule.mode_url(
                    varname=RuleGroup.SpecialAgents(self._bundle_group.split(":")[1]),
                    rule_id=rule.id,
                ),
                title=_("Rule"),
                icon="cloud",
                permission="rulesets",
                description=_(
                    'The rule set "{rule_title}" contains the special agent configuration. Credentials and other agent-specific data can be edited here'
                ).format(rule_title=rule.ruleset.title()),
            ),
            MenuItem(
                mode_or_url=ModeEditHost.mode_url(host=host.name()),
                title=_("Host"),
                icon="folder",
                permission="hosts",
                description=_(
                    'The host "{host_name}" contains all configuration like general properties and the folder location. Adjust to modify labels, tags or similar customization.'
                ).format(host_name=host.name()),
            ),
        ]

        if self._bundle_references.dcd_connections:
            dcd_config_id, dcd_config_spec = self._bundle_references.dcd_connections[0]
            bundle_entity_links.append(
                MenuItem(
                    mode_or_url=mode_url("edit_dcd_connection", ident=dcd_config_id),
                    title=_("Dynamic host management"),
                    icon="dcd_connections",
                    permission="dcd_connections",
                    description=_(
                        'Additional hosts are created automatically if they do not yet exist. Adjust the connection "{dcd_title}" to modify the folder or properties.'
                    ).format(dcd_title=dcd_config_spec["title"]),
                )
            )

        if self._bundle_references.passwords:
            password_id, password = self._bundle_references.passwords[0]
            bundle_entity_links.append(
                MenuItem(
                    mode_or_url=ModeEditPassword.mode_url(ident=password_id),
                    title=_("Password"),
                    icon="passwords",
                    permission="passwords",
                    description=_(
                        'All passwords, secrets and other sensitive data are stored in the Password Store. Changes to the entry "{password_title}" can be made here.'
                    ).format(password_title=password["title"]),
                )
            )
        TileMenuRenderer(bundle_entity_links, tile_size="large").show()

    def _page_section_bundle_configuration(self) -> None:
        with html.form_context("edit_bundle", method="POST"):
            self._configuration_vs(self._bundle_id).render_input(
                self.FORM_PREFIX,
                {
                    "_name": self._bundle["title"],
                    "_comment": self._bundle["comment"],
                },
            )
            forms.end()
            html.hidden_fields()

    @staticmethod
    def _configuration_vs(bundle_id: str) -> Dictionary:
        elements: Sequence[DictionaryEntry] = [
            ("_name", TextInput(title=_("Name"), size=80)),
            ("_comment", RuleComment()),
            (
                "_bundle_id",
                FixedValue(title=_("Configuration bundle ID"), value=bundle_id),
            ),
        ]
        return Dictionary(
            title=_("Configuration bundle properties"),
            optional_keys=False,
            render="form",
            elements=elements,
        )

    @override
    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(self.mode_url(bundle_id=self._bundle_id))

        if request.has_var("_clean_up"):
            references = identify_bundle_references(None, {self._bundle_id})[self._bundle_id]
            delete_config_bundle_objects(
                references,
                user_id=user.id,
                pprint_value=active_config.wato_pprint_config,
                use_git=active_config.wato_use_git,
                debug=active_config.debug,
            )
            return redirect(mode_url("changelog"))

        if request.has_var("_save"):
            vs = self._configuration_vs(self._bundle_id)
            config = vs.from_html_vars(self.FORM_PREFIX)
            vs.validate_value(config, "edit_bundle")
            self._bundle.update(
                {
                    "title": config["_name"],
                    "comment": config["_comment"],
                }
            )
            edit_config_bundle_configuration(
                self._bundle_id,
                self._bundle,
                pprint_value=active_config.wato_pprint_config,
            )

        return redirect(self.parent_mode().mode_url(varname=self._bundle_group))
