#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Predefine conditions that can be used in the Setup rule editor"""

from collections.abc import Collection

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.table import Table
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import (
    Alternative,
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    Transform,
    ValueSpec,
)
from cmk.gui.wato.pages.rulesets import VSExplicitConditions
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.predefined_conditions import PredefinedConditionSpec, PredefinedConditionStore
from cmk.gui.watolib.rulesets import AllRulesets, FolderRulesets, RuleConditions, UseHostFolder
from cmk.gui.watolib.rulespecs import RulespecGroup, ServiceRulespec

from ._simple_modes import SimpleEditMode, SimpleListMode, SimpleModeType


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModePredefinedConditions)
    mode_registry.register(ModeEditPredefinedCondition)


class DummyRulespecGroup(RulespecGroup):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def title(self) -> str:
        return "Dummy"

    @property
    def help(self):
        return "Dummy"


def dummy_rulespec() -> ServiceRulespec:
    return ServiceRulespec(
        name="dummy",
        group=DummyRulespecGroup,
        valuespec=lambda: FixedValue(value=None),
        item_type="service",
    )


def vs_conditions() -> Transform:
    return Transform(
        valuespec=VSExplicitConditions(rulespec=dummy_rulespec(), render="form_part"),
        to_valuespec=lambda c: RuleConditions.from_config("", c),
        from_valuespec=lambda c: c.to_config(UseHostFolder.HOST_FOLDER_FOR_UI),
    )


class PredefinedConditionModeType(SimpleModeType[PredefinedConditionSpec]):
    def type_name(self) -> str:
        return "predefined_condition"

    def name_singular(self) -> str:
        return _("predefined condition")

    def is_site_specific(self) -> bool:
        return False

    def can_be_disabled(self) -> bool:
        return False

    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return [ConfigDomainCore()]


class ModePredefinedConditions(SimpleListMode[PredefinedConditionSpec]):
    @classmethod
    def name(cls) -> str:
        return "predefined_conditions"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["rulesets"]

    def __init__(self) -> None:
        super().__init__(
            mode_type=PredefinedConditionModeType(),
            store=PredefinedConditionStore(),
        )
        self._contact_groups = load_contact_group_information()

    def title(self) -> str:
        return _("Predefined conditions")

    def _table_title(self) -> str:
        return _("Predefined conditions")

    def _validate_deletion(
        self, ident: str, entry: PredefinedConditionSpec, *, debug: bool
    ) -> None:
        if {
            name: ruleset
            for name, ruleset in AllRulesets.load_all_rulesets().get_rulesets().items()
            if ruleset.matches_search_with_rules({"rule_predefined_condition": ident}, debug=debug)
        }:
            raise MKUserError(
                "_delete",
                _('You can not delete this %s because it is <a href="%s">in use</a>.')
                % (self._mode_type.name_singular(), self._search_url(ident)),
            )

    def page(self) -> None:
        html.p(
            _(
                "This module can be used to define conditions for Checkmk rules in a central place. "
                "You can then refer to these conditions from different rule sets. Using these predefined "
                "conditions may save you a lot of redundant conditions when you need them in multiple "
                "rule sets."
            )
        )
        super().page()

    def _show_action_cell(
        self,
        nr: int,
        table: Table,
        ident: str,
        entry: PredefinedConditionSpec,
    ) -> None:
        super()._show_action_cell(nr, table, ident, entry)

        html.icon_button(
            self._search_url(ident),
            _("Show rules using this %s") % self._mode_type.name_singular(),
            "search",
        )

    def _search_url(self, ident: str) -> str:
        return makeuri_contextless(
            request,
            [
                ("mode", "rule_search"),
                ("filled_in", "rule_search"),
                ("search_p_rule_predefined_condition", DropdownChoice.option_id(ident)),
                ("search_p_rule_predefined_condition_USE", "on"),
            ],
        )

    def _show_entry_cells(self, table: Table, ident: str, entry: PredefinedConditionSpec) -> None:
        table.cell(_("Title"), entry["title"])

        table.cell(_("Conditions"))
        html.open_ul(class_="conditions")
        html.open_li()
        html.write_text_permissive(
            "{}: {}".format(
                _("Folder"), folder_tree().folder(entry["conditions"]["host_folder"]).alias_path()
            )
        )
        html.close_li()
        html.close_ul()
        html.write_text_permissive(vs_conditions().value_to_html(entry["conditions"]))

        table.cell(_("Editable by"))
        if entry["owned_by"] is None:
            html.write_text_permissive(
                _(
                    "Administrators (having the permission "
                    '"Write access to all predefined conditions")'
                )
            )
        else:
            html.write_text_permissive(self._contact_group_alias(entry["owned_by"]))

        table.cell(_("Shared with"))
        if not entry["shared_with"]:
            html.write_text_permissive(_("Not shared"))
        else:
            html.write_text_permissive(
                ", ".join([self._contact_group_alias(g) for g in entry["shared_with"]])
            )

    def _contact_group_alias(self, name: str) -> str:
        return self._contact_groups.get(name, {"alias": name})["alias"]


class ModeEditPredefinedCondition(SimpleEditMode[PredefinedConditionSpec]):
    @classmethod
    def name(cls) -> str:
        return "edit_predefined_condition"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["rulesets"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModePredefinedConditions

    def __init__(self) -> None:
        super().__init__(
            mode_type=PredefinedConditionModeType(),
            store=PredefinedConditionStore(),
        )

    def _vs_individual_elements(self) -> list[DictionaryEntry]:
        if user.may("wato.edit_all_predefined_conditions"):
            admin_element: list[ValueSpec] = [
                FixedValue(
                    value=None,
                    title=_("Administrators"),
                    totext=_(
                        "Administrators (having the permission "
                        '"Write access to all predefined conditions")'
                    ),
                )
            ]
        else:
            admin_element = []

        return [
            ("conditions", vs_conditions()),
            (
                "owned_by",
                Alternative(
                    title=_("Editable by"),
                    help=_(
                        "Each predefined condition is owned by a group of users which are able to edit, "
                        "delete and use existing predefined conditions."
                    ),
                    elements=admin_element
                    + [
                        DropdownChoice(
                            title=_("Members of the contact group:"),
                            choices=lambda: self._contact_group_choices(only_own=True),
                            invalid_choice="complain",
                            empty_text=_(
                                "You need to be member of at least one contact group to be able to "
                                "create a predefined condition."
                            ),
                            invalid_choice_title=_("Group not existant or not member"),
                            invalid_choice_error=_(
                                "The choosen group is either not existant "
                                "anymore or you are not a member of this "
                                "group. Please choose another one."
                            ),
                        ),
                    ],
                ),
            ),
            (
                "shared_with",
                DualListChoice(
                    title=_("Share with"),
                    help=_(
                        "By default only the members of the owner contact group are permitted "
                        "to use a a predefined condition. It is possible to share it with "
                        "other groups of users to make them able to use a predefined condition in rules."
                    ),
                    choices=self._contact_group_choices,
                    autoheight=False,
                ),
            ),
        ]

    def _save(self, entries: dict[str, PredefinedConditionSpec]) -> None:
        # In case it already existed before, remember the previous path
        old_entries = self._store.load_for_reading()
        old_path = None
        if self._ident in old_entries:
            old_path = self._store.load_for_reading()[self._ident]["conditions"]["host_folder"]

        super()._save(entries)

        assert self._ident is not None
        conditions = RuleConditions.from_config("", entries[self._ident]["conditions"])

        # Update rules of source folder in case the folder was changed
        if old_path is not None and old_path != conditions.host_folder:
            self._move_rules_for_conditions(conditions, old_path)

        self._rewrite_rules_for(conditions)

    def _move_rules_for_conditions(self, conditions: RuleConditions, old_path: str) -> None:
        """Apply changed folder of predefined condition to rules"""
        tree = folder_tree()
        old_folder = tree.folder(old_path)
        old_rulesets = FolderRulesets.load_folder_rulesets(old_folder)

        new_folder = tree.folder(conditions.host_folder)
        new_rulesets = FolderRulesets.load_folder_rulesets(new_folder)

        for old_ruleset in old_rulesets.get_rulesets().values():
            for rule in old_ruleset.get_folder_rules(old_folder):
                if rule.predefined_condition_id() == self._ident:
                    old_ruleset.delete_rule(rule)

                    new_ruleset = new_rulesets.get(old_ruleset.name)
                    new_ruleset.append_rule(new_folder, rule)

        new_rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )
        old_rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )

    def _rewrite_rules_for(self, conditions: RuleConditions) -> None:
        """Apply changed predefined condition to rules

        After updating a predefined condition it is necessary to rewrite the
        rules.mk the predefined condition refers to. Rules in this file may refer to
        the changed predefined condition. Since the conditions are only applied to the
        rules while saving them this step is needed.
        """
        folder = folder_tree().folder(conditions.host_folder)
        rulesets = FolderRulesets.load_folder_rulesets(folder)

        for ruleset in rulesets.get_rulesets().values():
            for rule in ruleset.get_folder_rules(folder):
                if rule.predefined_condition_id() == self._ident:
                    rule.update_conditions(conditions)

        rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )

    def _contact_group_choices(self, only_own: bool = False) -> list[tuple[str, str]]:
        contact_groups = load_contact_group_information()

        if only_own:
            assert user.id is not None
            user_groups = userdb.contactgroups_of_user(user.id)
        else:
            user_groups = []

        entries = [
            (c, g["alias"]) for c, g in contact_groups.items() if not only_own or c in user_groups
        ]
        return sorted(entries, key=lambda x: x[1])
