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
"""Predefine conditions that can be used in the WATO rule editor"""

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    FixedValue,
    Alternative,
    DropdownChoice,
    DualListChoice,
    Transform,
)

from cmk.gui.plugins.wato.check_mk_configuration import RulespecGroupUserInterface
from cmk.gui.wato.pages.rulesets import VSExplicitConditions, RuleConditions
from cmk.gui.watolib.rulesets import AllRulesets, SearchedRulesets, FolderRulesets
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulespecs import ServiceRulespec
from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.gui.plugins.wato import (
    ConfigDomainGUI,
    SimpleModeType,
    SimpleListMode,
    SimpleEditMode,
    mode_registry,
)


def dummy_rulespec():
    rulespec_class = type("DummyRulespec", (ServiceRulespec,), {
        "group": RulespecGroupUserInterface,
        "name": "dummy",
        "valuespec": None,
    })
    # Pylint does not get this right for some reason
    return rulespec_class()  # pylint: disable=abstract-class-instantiated


def vs_conditions():
    return Transform(
        VSExplicitConditions(rulespec=dummy_rulespec(), render="form_part"),
        forth=lambda c: RuleConditions(None).from_config(c),
        back=lambda c: c.to_config_with_folder(),
    )


class PredefinedConditionModeType(SimpleModeType):
    def type_name(self):
        return "predefined_condition"

    def name_singular(self):
        return _("predefined condition")

    def is_site_specific(self):
        return False

    def can_be_disabled(self):
        return False

    def affected_config_domains(self):
        return [ConfigDomainGUI]


@mode_registry.register
class ModePredefinedConditions(SimpleListMode):
    @classmethod
    def name(cls):
        return "predefined_conditions"

    @classmethod
    def permissions(cls):
        return ["rulesets"]

    def __init__(self):
        super(ModePredefinedConditions, self).__init__(
            mode_type=PredefinedConditionModeType(),
            store=PredefinedConditionStore(),
        )
        self._contact_groups = load_contact_group_information()

    def title(self):
        return _("Predefined conditions")

    def _table_title(self):
        return _("Predefined conditions")

    def _validate_deletion(self, ident, entry):
        rulesets = AllRulesets()
        rulesets.load()
        matched_rulesets = SearchedRulesets(rulesets, {
            "rule_predefined_condition": ident
        }).get_rulesets()

        if matched_rulesets:
            raise MKUserError(
                "_delete",
                _("You can not delete this %s because it is <a href=\"%s\">in use</a>.") %
                (self._mode_type.name_singular(), self._search_url(ident)))

    def page(self):
        html.p(
            _("This module can be used to define conditions for Check_MK rules in a central place. "
              "You can then refer to these conditions from different rulesets. Using these predefined "
              "conditions may save you a lot of redundant conditions when you need them in multiple "
              "rulesets."))
        super(ModePredefinedConditions, self).page()

    def _show_action_cell(self, table, ident):
        super(ModePredefinedConditions, self)._show_action_cell(table, ident)

        html.icon_button(
            self._search_url(ident),
            _("Show rules using this %s") % self._mode_type.name_singular(), "search")

    def _search_url(self, ident):
        return html.makeuri_contextless([("mode", "rulesets"),
                                         ("search_p_rule_predefined_condition",
                                          DropdownChoice.option_id(ident)),
                                         ("search_p_rule_predefined_condition_USE", "on")])

    def _show_entry_cells(self, table, ident, entry):
        table.cell(_("Title"), html.render_text(entry["title"]))

        table.cell(_("Conditions"))
        html.open_ul(class_="conditions")
        html.open_li()
        html.write("%s: %s" % (_("Folder"), Folder.folder(
            entry["conditions"]["host_folder"]).alias_path()))
        html.close_li()
        html.close_ul()
        html.write(vs_conditions().value_to_text(entry["conditions"]))

        table.cell(_("Editable by"))
        if entry["owned_by"] is None:
            html.write_text(
                _("Administrators (having the permission "
                  "\"Write access to all predefined conditions\")"))
        else:
            html.write_text(self._contact_group_alias(entry["owned_by"]))

        table.cell(_("Shared with"))
        if not entry["shared_with"]:
            html.write_text(_("Not shared"))
        else:
            html.write_text(", ".join([self._contact_group_alias(g) for g in entry["shared_with"]]))

    def _contact_group_alias(self, name):
        return self._contact_groups.get(name, {"alias": name})["alias"]


@mode_registry.register
class ModeEditPredefinedCondition(SimpleEditMode):
    @classmethod
    def name(cls):
        return "edit_predefined_condition"

    @classmethod
    def permissions(cls):
        return ["rulesets"]

    def __init__(self):
        super(ModeEditPredefinedCondition, self).__init__(
            mode_type=PredefinedConditionModeType(),
            store=PredefinedConditionStore(),
        )

    def _vs_individual_elements(self):
        if config.user.may("wato.edit_all_predefined_conditions"):
            admin_element = [
                FixedValue(
                    None,
                    title=_("Administrators"),
                    totext=_("Administrators (having the permission "
                             "\"Write access to all predefined conditions\")"),
                )
            ]
        else:
            admin_element = []

        return [
            ("conditions", vs_conditions()),
            ("owned_by",
             Alternative(
                 title=_("Editable by"),
                 help=_(
                     "Each predefined condition is owned by a group of users which are able to edit, "
                     "delete and use existing predefined conditions."),
                 style="dropdown",
                 elements=admin_element + [
                     DropdownChoice(
                         title=_("Members of the contact group:"),
                         choices=lambda: self._contact_group_choices(only_own=True),
                         invalid_choice="complain",
                         empty_text=_(
                             "You need to be member of at least one contact group to be able to "
                             "create a predefined condition."),
                         invalid_choice_title=_("Group not existant or not member"),
                         invalid_choice_error=_("The choosen group is either not existant "
                                                "anymore or you are not a member of this "
                                                "group. Please choose another one."),
                     ),
                 ])),
            ("shared_with",
             DualListChoice(
                 title=_("Share with"),
                 help=_(
                     "By default only the members of the owner contact group are permitted "
                     "to use a a predefined condition. It is possible to share it with "
                     "other groups of users to make them able to use a predefined condition in rules."
                 ),
                 choices=self._contact_group_choices,
                 autoheight=False,
             )),
        ]

    def _save(self, entries):
        # In case it already existed before, remember the previous path
        old_entries = self._store.load_for_reading()
        old_path = None
        if self._ident in old_entries:
            old_path = self._store.load_for_reading()[self._ident]["conditions"]["host_folder"]

        super(ModeEditPredefinedCondition, self)._save(entries)

        conditions = RuleConditions(None).from_config(entries[self._ident]["conditions"])

        # Update rules of source folder in case the folder was changed
        if old_path is not None and old_path != conditions.host_folder:
            self._move_rules_for_conditions(conditions, old_path)

        self._rewrite_rules_for(conditions)

    def _move_rules_for_conditions(self, conditions, old_path):
        # type (RuleConditions, str) -> None
        """Apply changed folder of predefined condition to rules"""
        old_folder = Folder.folder(old_path)
        old_rulesets = FolderRulesets(old_folder)
        old_rulesets.load()

        new_folder = Folder.folder(conditions.host_folder)
        new_rulesets = FolderRulesets(new_folder)
        new_rulesets.load()

        for old_ruleset in old_rulesets.get_rulesets().values():
            for rule in old_ruleset.get_folder_rules(old_folder):
                if rule.predefined_condition_id() == self._ident:
                    old_ruleset.delete_rule(rule)

                    new_ruleset = new_rulesets.get(old_ruleset.name)
                    new_ruleset.append_rule(new_folder, rule)

        new_rulesets.save()
        old_rulesets.save()

    def _rewrite_rules_for(self, conditions):
        # type: (RuleConditions) -> None
        """Apply changed predefined condition to rules

        After updating a predefined condition it is necessary to rewrite the
        rules.mk the predefined condition refers to. Rules in this file may refer to
        the changed predefined condition. Since the conditions are only applied to the
        rules while saving them this step is needed.
        """
        folder = Folder.folder(conditions.host_folder)
        rulesets = FolderRulesets(folder)
        rulesets.load()

        for ruleset in rulesets.get_rulesets().values():
            for rule in ruleset.get_folder_rules(folder):
                if rule.predefined_condition_id() == self._ident:
                    rule.update_conditions(conditions)

        rulesets.save()

    def _contact_group_choices(self, only_own=False):
        contact_groups = load_contact_group_information()

        if only_own:
            user_groups = userdb.contactgroups_of_user(config.user.id)
        else:
            user_groups = []

        entries = [
            (c, g['alias']) for c, g in contact_groups.items() if not only_own or c in user_groups
        ]
        return sorted(entries, key=lambda x: x[1])
