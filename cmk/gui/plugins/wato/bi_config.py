#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO-Module for the rules and aggregations of Check_MK BI"""

import json
import copy
from typing import Dict, Any, List, Type, Tuple as _Tuple, Optional as _Optional, overload

import cmk.utils.version as cmk_version
import cmk.gui.escaping as escaping
from cmk.gui.pages import page_registry, AjaxPage

try:
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
except ImportError:
    managed = None  # type: ignore[assignment]

import cmk.gui.config as config
from cmk.gui.table import table_element
import cmk.gui.forms as forms
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKUserError, MKGeneralException, MKAuthException
from cmk.gui.valuespec import (
    ValueSpec,
    Transform,
    Alternative,
    FixedValue,
    TextAscii,
    Dictionary,
    IconSelector,
    ListOf,
    ListOfStrings,
    Checkbox,
    TextUnicode,
    TextAreaUnicode,
    Optional,
    ID,
    DropdownChoice,
)

from cmk.gui.i18n import _, _l
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML, Choices
from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    ContactGroupSelection,
    MainMenu,
    MenuItem,
    main_module_registry,
    ABCMainModule,
    MainModuleTopicBI,
    add_change,
    PermissionSectionWATO,
    redirect,
    mode_url,
)

from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuPopup,
    make_simple_link,
    make_simple_form_page_menu,
    make_confirmed_form_submit_link,
    make_checkbox_selection_topic,
)

from cmk.gui.node_visualization import BILayoutManagement
from cmk.utils.bi.bi_aggregation_functions import BIAggregationFunctionSchema
from cmk.utils.bi.bi_packs import BIAggregationPack
from cmk.utils.bi.bi_rule import BIRule, BIRuleSchema
from cmk.utils.bi.bi_aggregation import BIAggregation, BIAggregationSchema
from cmk.gui.permissions import (
    permission_registry,
    Permission,
)
from cmk.gui.bi import get_cached_bi_packs, BIManager, bi_livestatus_query

# TODO: forbidden import, integrate into bi_config... ?
import cmk.gui.plugins.wato.bi_valuespecs as bi_valuespecs
import cmk.gui.sites
from cmk.utils.bi.bi_actions import BICallARuleAction
from cmk.utils.bi.bi_lib import SitesCallback
from cmk.utils.bi.bi_compiler import BICompiler

from cmk.gui.utils.urls import makeuri, makeuri_contextless, make_confirm_link


@main_module_registry.register
class MainModuleBI(ABCMainModule):
    @property
    def mode_or_url(self):
        return "bi_packs"

    @property
    def topic(self):
        return MainModuleTopicBI

    @property
    def title(self):
        return _("Business Intelligence")

    @property
    def icon(self):
        return "aggr"

    @property
    def permission(self):
        return "bi_rules"

    @property
    def description(self):
        return _("Configuration of Checkmk's Business Intelligence component")

    @property
    def sort_index(self):
        return 70

    @property
    def is_show_more(self):
        return True


#.
#   .--Edit Pack-----------------------------------------------------------.
#   |               _____    _ _ _     ____            _                   |
#   |              | ____|__| (_) |_  |  _ \ __ _  ___| | __               |
#   |              |  _| / _` | | __| | |_) / _` |/ __| |/ /               |
#   |              | |__| (_| | | |_  |  __/ (_| | (__|   <                |
#   |              |_____\__,_|_|\__| |_|   \__,_|\___|_|\_\               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ABCBIMode(WatoMode):
    def __init__(self):
        super().__init__()
        self._bi_packs = get_cached_bi_packs()
        self._bi_pack = None

        # Most modes need a pack as context
        self._bi_pack = self._get_pack_from_request()

    def _get_pack_from_request(self) -> _Optional[BIAggregationPack]:
        if html.request.has_var("pack"):
            pack_id = html.request.get_str_input_mandatory("pack")
            try:
                return self._bi_packs.get_pack_mandatory(pack_id)
            except KeyError:
                raise MKUserError("pack", _("This BI pack does not exist: %s") % pack_id)
        return None

    @property
    def bi_pack(self) -> BIAggregationPack:
        assert self._bi_pack is not None
        return self._bi_pack

    def verify_pack_permission(self, bi_pack):
        if not bi_valuespecs.is_contact_for_pack(bi_pack):
            raise MKAuthException(
                _("You have no permission for changes in this BI pack %s.") % bi_pack.title)

    def title(self):
        return _("Business Intelligence")

    def title_for_pack(self, bi_pack):
        return escaping.escape_attribute(bi_pack.title)

    def _add_change(self, action_name, text):
        site_ids = list(config.wato_slave_sites().keys()) + [config.omd_site()]
        add_change(action_name, text, domains=[watolib.ConfigDomainGUI], sites=site_ids)

    def url_to_pack(self, addvars, bi_pack):
        return makeuri_contextless(request, addvars + [("pack", bi_pack.id)])

    def _get_selection(self, _type):
        checkbox_name = "_c_%s_" % _type
        return [
            varname.split(checkbox_name)[-1]  #
            for varname, _value in html.request.itervars(prefix=checkbox_name)
            if html.get_checkbox(varname)
        ]

    def render_rule_tree(self, rule_id, tree_path, tree_prefix=""):
        bi_pack = self._bi_packs.get_pack_of_rule(rule_id)
        if bi_pack is None:
            raise MKUserError("pack", _("This BI pack does not exist."))
        bi_rule = bi_pack.get_rule(rule_id)
        if bi_rule is None:
            raise MKUserError("pack", _("This BI rule does not exist."))

        edit_url = makeuri_contextless(
            request,
            [("mode", "bi_edit_rule"), ("id", bi_rule.id), ("pack", bi_pack.id)],
        )
        title = "%s (%s)" % (bi_rule.properties.title, bi_rule.id)

        sub_rule_ids = self.aggregation_sub_rule_ids(bi_rule)
        if not sub_rule_ids:
            html.open_li()
            html.open_a(href=edit_url)
            html.write_text(title)
            html.close_a()
            html.close_li()
        else:
            html.begin_foldable_container("bi_rule_trees",
                                          "%s%s" % (tree_prefix, tree_path),
                                          False,
                                          title,
                                          title_url=edit_url)
            for sub_rule_id in sub_rule_ids:
                self.render_rule_tree(sub_rule_id, tree_path + "/" + sub_rule_id, tree_prefix)
            html.end_foldable_container()

    def aggregation_sub_rule_ids(self, bi_rule):
        sub_rule_ids = []
        for bi_node in bi_rule.get_nodes():
            if bi_node.action.type() == BICallARuleAction.type():
                sub_rule_ids.append(bi_node.action.rule_id)
        return sub_rule_ids

    def _add_rule_arguments_lookup(self):
        allowed_rules = self._allowed_rules()
        lookup = {}
        for bi_rule in allowed_rules.values():
            lookup[DropdownChoice.option_id(bi_rule.id)] = bi_rule.params.arguments

        html.javascript("""var bi_rule_argument_lookup = %s;
        cmk.bi.update_argument_hints();
""" % json.dumps(lookup))

    def _allowed_rules(self):
        allowed_rules = {}
        for bi_pack in sorted(self._bi_packs.get_packs().values(), key=lambda p: p.title):
            if bi_valuespecs.may_use_rules_in_pack(bi_pack):
                allowed_rules.update(bi_pack.get_rules())
        return allowed_rules


@mode_registry.register
class ModeBIEditPack(ABCBIMode):
    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeBIPacks

    @classmethod
    def name(cls):
        return "bi_edit_pack"

    @classmethod
    def permissions(cls):
        return ["bi_rules", "bi_admin"]

    def title(self):
        if self._bi_pack:
            return super().title() + " - " + _("Edit BI Pack %s") % self.bi_pack.title
        return super().title() + " - " + _("Add BI Pack")

    def action(self) -> ActionResult:
        if html.check_transaction():
            vs_config = self._vs_pack().from_html_vars("bi_pack")
            self._vs_pack().validate_value(vs_config, 'bi_pack')
            if self._bi_pack:
                self.bi_pack.title = vs_config["title"]
                self.bi_pack.contact_groups = vs_config["contact_groups"]
                self.bi_pack.public = vs_config["public"]
                self._add_change("bi-edit-pack", _("Modified BI pack %s") % self.bi_pack.id)
            else:
                if self._bi_packs.pack_exists(vs_config["id"]):
                    raise MKUserError("pack_id", _("A BI pack with this ID already exists."))
                self._add_change("bi-new-pack", _("Added new BI pack %s") % vs_config["id"])
                vs_config["rules"] = {}
                vs_config["aggregations"] = {}
                self._bi_packs.add_pack(BIAggregationPack(vs_config))
            self._bi_packs.save_config()

        return redirect(mode_url("bi_packs"))

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb,
                                          form_name="bi_pack",
                                          button_name="_save",
                                          save_title=_("Save") if self._bi_pack else _("Create"))

    def page(self):
        html.begin_form("bi_pack", method="POST")

        if self._bi_pack is None:
            vs_config = self._vs_pack().from_html_vars("bi_pack")
        else:
            vs_config = {
                "id": self.bi_pack.id,
                "title": self.bi_pack.title,
                "contact_groups": self.bi_pack.contact_groups,
                "public": self.bi_pack.public,
            }
        self._vs_pack().render_input("bi_pack", vs_config)
        forms.end()
        html.hidden_fields()
        if self._bi_pack:
            html.set_focus("bi_pack_p_title")
        else:
            html.set_focus("bi_pack_p_id")
        html.end_form()

    def _vs_pack(self):
        if self._bi_pack:
            id_element = FixedValue(title=_("Pack ID"), value=self.bi_pack.id)
        else:
            id_element = ID(
                title=_("BI pack ID"),
                help=_("A unique ID of this BI pack."),
                allow_empty=False,
                size=24,
            )
        return Dictionary(
            title=_("BI Pack Properties"),
            optional_keys=False,
            render="form",
            elements=
            [("id", id_element),
             ("title",
              TextUnicode(
                  title=_("Title"),
                  help=_("A descriptive title for this rule pack"),
                  allow_empty=False,
                  size=64,
              )),
             ("contact_groups",
              ListOf(
                  ContactGroupSelection(),
                  title=_("Permitted Contact Groups"),
                  help=_(
                      "The rules and aggregations in this pack can be edited by all members of the "
                      "contact groups specified here - even if they have no administrator priviledges."
                  ),
                  movable=False,
                  add_label=_("Add Contact Group"),
              )),
             ("public",
              Checkbox(
                  title=_("Public"),
                  label=_("Allow all users to refer to rules contained in this pack"),
                  help=_("Without this option users can only use rules if they have administrator "
                         "priviledges or are member of the listed contact groups."),
              ))],
        )


#   .--BIPacks-------------------------------------------------------------.
#   |                  ____ ___ ____            _                          |
#   |                 | __ )_ _|  _ \ __ _  ___| | _____                   |
#   |                 |  _ \| || |_) / _` |/ __| |/ / __|                  |
#   |                 | |_) | ||  __/ (_| | (__|   <\__ \                  |
#   |                 |____/___|_|   \__,_|\___|_|\_\___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@mode_registry.register
class ModeBIPacks(ABCBIMode):
    def __init__(self):
        super().__init__()
        self._contact_group_names = load_contact_group_information()

    @classmethod
    def name(cls):
        return "bi_packs"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        bi_config_entries = []
        if config.user.may("wato.bi_admin"):
            bi_config_entries.append(
                PageMenuEntry(
                    title=_("Add BI pack"),
                    icon_name="new",
                    item=make_simple_link(makeuri_contextless(request, [("mode", "bi_edit_pack")])),
                    is_shortcut=True,
                    is_suggested=True,
                ))

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="packs",
                    title=_("BI Packs"),
                    topics=[
                        PageMenuTopic(
                            title=_("BI configuration"),
                            entries=bi_config_entries,
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="services",
                    title=_("Services"),
                    topics=[
                        PageMenuTopic(
                            title=_("Of aggregations"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Monitor state"),
                                    icon_name="rulesets",
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [
                                                ("mode", "edit_ruleset"),
                                                ("varname", "special_agents:bi"),
                                            ],
                                        )),
                                ),
                                PageMenuEntry(
                                    title=_("Monitor single state (Deprecated)"),
                                    icon_name="rulesets",
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [
                                                ("mode", "edit_ruleset"),
                                                ("varname", "active_checks:bi_aggr"),
                                            ],
                                        )),
                                    is_show_more=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return redirect(self.mode_url())

        if not html.request.has_var("_delete"):
            return redirect(self.mode_url())

        config.user.need_permission("wato.bi_admin")

        pack_id = html.request.get_str_input_mandatory("_delete")
        pack = self._bi_packs.get_pack(pack_id)
        if pack is None:
            raise MKUserError("_delete", _("This BI pack does not exist."))

        if pack.num_rules() > 0:
            raise MKUserError(
                None,
                _("You cannot delete this pack. It contains <b>%d</b> rules.") % pack.num_rules())

        self._add_change("delete-bi-pack", _("Deleted BI pack %s") % pack_id)
        self._bi_packs.delete_pack(pack_id)
        self._bi_packs.save_config()
        return redirect(self.mode_url())

    def page(self):
        with table_element(title=_("BI Configuration Packs")) as table:
            for pack in sorted(self._bi_packs.packs.values(), key=lambda x: x.id):
                if not bi_valuespecs.may_use_rules_in_pack(pack):
                    continue

                table.row()
                table.cell(_("Actions"), css="buttons")
                if config.user.may("wato.bi_admin"):
                    target_mode = "bi_edit_pack"
                    edit_url = makeuri_contextless(
                        request,
                        [("mode", target_mode), ("pack", pack.id)],
                    )
                    html.icon_button(edit_url, _("Edit properties of this BI pack"), "edit")
                    delete_url = make_confirm_link(
                        url=html.makeactionuri([("_delete", pack.id)]),
                        message=_("Do you really want to delete the BI pack "
                                  "<b>%s</b> <i>%s</i> with <b>%d</b> aggregations?") %
                        (pack.id, pack.title, pack.num_aggregations()))
                    html.icon_button(delete_url, _("Delete this BI pack"), "delete")
                rules_url = makeuri_contextless(request, [("mode", "bi_rules"), ("pack", pack.id)])
                html.icon_button(rules_url,
                                 _("View and edit the rules and aggregations in this BI pack"),
                                 "bi_rules")
                table.text_cell(_("ID"), pack.id)
                table.text_cell(_("Title"), pack.title)
                table.text_cell(_("Public"), pack.public and _("Yes") or _("No"))
                table.text_cell(_("Aggregations"), len(pack.aggregations), css="number")
                table.text_cell(_("Rules"), len(pack.rules), css="number")
                table.text_cell(
                    _("Contact groups"),
                    HTML(", ").join(map(self._render_contact_group, pack.contact_groups)))

    def _render_contact_group(self, c):
        display_name = self._contact_group_names.get(c, {'alias': c})['alias']
        return html.render_a(display_name, "wato.py?mode=edit_contact_group&edit=%s" % c)


#   .--BIRules-------------------------------------------------------------.
#   |                  ____ ___ ____        _                              |
#   |                 | __ )_ _|  _ \ _   _| | ___  ___                    |
#   |                 |  _ \| || |_) | | | | |/ _ \/ __|                   |
#   |                 | |_) | ||  _ <| |_| | |  __/\__ \                   |
#   |                 |____/___|_| \_\\__,_|_|\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@mode_registry.register
class ModeBIRules(ABCBIMode):
    @classmethod
    def name(cls):
        return "bi_rules"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, pack: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def __init__(self):
        super().__init__()
        self._view_type = html.request.var("view", "list")

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeBIPacks

    def _breadcrumb_url(self) -> str:
        return self.mode_url(pack=self.bi_pack.id)

    def title(self):
        if self._view_type == "list":
            return self.title_for_pack(self.bi_pack) + " - " + _("Rules")
        return self.title_for_pack(self.bi_pack) + " - " + _("Unused Rules")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        rules_entries = []
        if bi_valuespecs.is_contact_for_pack(self.bi_pack):
            rules_entries.append(
                PageMenuEntry(
                    title=_("Add rule"),
                    icon_name="new",
                    item=make_simple_link(self.url_to_pack([("mode", "bi_edit_rule")],
                                                           self.bi_pack)),
                    is_shortcut=True,
                    is_suggested=True,
                ))

        if self._view_type == "list":
            unused_rules_title = _("Show only unused rules")
            unused_rules_url = self.url_to_pack([("mode", "bi_rules")], self.bi_pack)
        else:
            unused_rules_title = _("Show all rules")
            unused_rules_url = self.url_to_pack([("mode", "bi_rules"), ("view", "unused")],
                                                self.bi_pack)

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rules",
                    title=_("Rules"),
                    topics=[
                        PageMenuTopic(
                            title=_("In this pack"),
                            entries=rules_entries,
                        ),
                        PageMenuTopic(
                            title=_("On selected rules"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Delete rules"),
                                    icon_name="delete",
                                    item=make_confirmed_form_submit_link(
                                        form_name="bulk_action_form",
                                        button_name="_bulk_delete_bi_rules",
                                        message=_(
                                            "Do you really want to delete the selected rules?"),
                                    ),
                                    is_enabled=bool(self.bi_pack and self.bi_pack.num_rules() > 0),
                                ),
                                PageMenuEntry(
                                    title=_("Move rules"),
                                    icon_name="move",
                                    name="move_rules",
                                    item=PageMenuPopup(self._render_bulk_move_form()),
                                    is_enabled=bool(self.bi_pack and
                                                    self.bi_pack.num_rules() > 0 and
                                                    self._show_bulk_move_choices()),
                                ),
                            ],
                        ),
                        make_checkbox_selection_topic(),
                    ],
                ),
                PageMenuDropdown(
                    name="aggregations",
                    title=_("Aggregations"),
                    topics=[
                        PageMenuTopic(
                            title=_("In this pack"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Aggregations"),
                                    icon_name="aggr",
                                    item=make_simple_link(
                                        self.url_to_pack([("mode", "bi_aggregations")],
                                                         self.bi_pack),),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="view",
                    title=_("View"),
                    topics=[
                        PageMenuTopic(
                            title=_("Filter"),
                            entries=[
                                PageMenuEntry(
                                    title=unused_rules_title,
                                    icon_name="unusedbirules",
                                    item=make_simple_link(unused_rules_url),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        self.verify_pack_permission(self.bi_pack)

        if not html.check_transaction():
            return redirect(self.mode_url(pack=self.bi_pack.id))

        if html.request.var("_del_rule"):
            self._delete_after_confirm()

        elif html.request.var("_bulk_delete_bi_rules"):
            self._bulk_delete_after_confirm()

        elif html.request.var("_bulk_move_bi_rules"):
            self._bulk_move_after_confirm()

        return redirect(self.mode_url(pack=self.bi_pack.id))

    def _delete_after_confirm(self) -> None:
        rule_id = html.request.get_str_input_mandatory("_del_rule")
        self._check_delete_rule_id_permission(rule_id)
        self._bi_packs.delete_rule(rule_id)
        self._add_change("bi-delete-rule", _("Deleted BI rule with ID %s") % rule_id)
        self._bi_packs.save_config()

    def _bulk_delete_after_confirm(self) -> None:
        selection = self._get_selection("rule")
        for rule_id in selection:
            self._check_delete_rule_id_permission(rule_id)

        if not selection:
            return

        for rule_id in selection:
            self._bi_packs.delete_rule(rule_id)
            self._add_change("bi-delete-rule", _("Deleted BI rule with ID %s") % rule_id)
        self._bi_packs.save_config()

    def _check_delete_rule_id_permission(self, rule_id) -> None:
        aggr_refs, rule_refs, _level = self._bi_packs.count_rule_references(rule_id)
        if aggr_refs:
            raise MKUserError(None,
                              _("You cannot delete this rule: it is still used by aggregations."))
        if rule_refs:
            raise MKUserError(None,
                              _("You cannot delete this rule: it is still used by other rules."))

    def _bulk_move_after_confirm(self) -> None:
        target_pack_id = None
        if html.request.has_var('bulk_moveto'):
            target_pack_id = html.request.get_str_input_mandatory('bulk_moveto', '')
            html.javascript('cmk.selection.update_bulk_moveto("%s")' % target_pack_id)

        if target_pack_id is None:
            raise MKUserError(None, _("This BI pack does not exist."))

        target_pack = self._bi_packs.get_pack(target_pack_id)
        if target_pack is None:
            raise MKUserError(None, _("This BI pack does not exist."))

        self.verify_pack_permission(target_pack)

        selection = self._get_selection("rule")
        if not selection:
            return None

        for rule_id in selection:
            bi_rule = self.bi_pack.get_rule_mandatory(rule_id)
            target_pack.add_rule(bi_rule)
            self._bi_packs.delete_rule(bi_rule.id)
            self._add_change(
                "bi-move-rule",
                _("Moved BI rule with ID %s to BI pack %s") % (rule_id, target_pack_id))
        self._bi_packs.save_config()

    def page(self):
        self.verify_pack_permission(self.bi_pack)
        if self.bi_pack.num_aggregations() == 0 and self.bi_pack.num_rules() == 0:
            menu = MainMenu()
            menu.add_item(
                MenuItem(
                    mode_or_url=self.url_to_pack([("mode", "bi_edit_rule")], self.bi_pack),
                    title=_("Add BI rule"),
                    icon="new",
                    permission="bi_rules",
                    description=_("Rules are the nodes in BI aggregations. "
                                  "Each aggregation has one rule as its root."),
                ))
            menu.show()
            return

        html.begin_form("bulk_action_form", method="POST")
        if self._view_type == "list":
            self.render_rules(_("Rules"), only_unused=False)
        else:
            self.render_rules(_("Unused BI Rules"), only_unused=True)

        html.hidden_fields()
        html.end_form()

    def _render_bulk_move_form(self) -> str:
        with html.plugged():
            move_choices = self._show_bulk_move_choices()
            if not move_choices:
                return ""

            if html.request.has_var('bulk_moveto'):
                html.javascript('cmk.selection.update_bulk_moveto("%s")' %
                                html.request.var('bulk_moveto', ''))

            html.add_confirm_on_submit("bulk_action_form",
                                       _("Do you really want to move the selected rules?"))

            html.dropdown("bulk_moveto",
                          move_choices,
                          "@",
                          onchange="cmk.selection.update_bulk_moveto(this.value)",
                          class_='bulk_moveto',
                          label=_("Move to pack: "),
                          form="form_bulk_action_form")

            html.button("_bulk_move_bi_rules",
                        _("Bulk move"),
                        "submit",
                        form="form_bulk_action_form")

            return html.drain()

    def _show_bulk_move_choices(self):
        return [(pack_id, bi_pack.title)
                for pack_id, bi_pack in self._bi_packs.get_packs().items()
                if pack_id is not self.bi_pack.id and bi_valuespecs.is_contact_for_pack(bi_pack)]

    def render_rules(self, title, only_unused):
        aggregations_that_use_rule = self._find_aggregation_rule_usages()

        rules = self.bi_pack.get_rules().items()
        # Sort rules according to nesting level, and then to id
        rules_refs = [(rule_id, rule, self._bi_packs.count_rule_references(rule_id))
                      for (rule_id, rule) in rules]
        rules_refs.sort(key=lambda x: (x[1].properties.title, x[2][2]))

        with table_element("bi_rules", title) as table:
            for rule_id, bi_rule, (aggr_refs, rule_refs, level) in rules_refs:
                refs = aggr_refs + rule_refs
                if not only_unused or refs == 0:
                    table.row()
                    table.cell(html.render_input("_toggle_group",
                                                 type_="button",
                                                 class_="checkgroup",
                                                 onclick="cmk.selection.toggle_all_rows();",
                                                 value='X'),
                               sortable=False,
                               css="checkbox")
                    html.checkbox("_c_rule_%s" % rule_id)

                    table.cell(_("Actions"), css="buttons")
                    edit_url = self.url_to_pack([("mode", "bi_edit_rule"), ("id", rule_id)],
                                                self.bi_pack)
                    html.icon_button(edit_url, _("Edit this rule"), "edit")

                    clone_url = self.url_to_pack([("mode", "bi_edit_rule"), ("clone", rule_id)],
                                                 self.bi_pack)
                    html.icon_button(clone_url, _("Create a copy of this rule"), "clone")

                    if rule_refs == 0:
                        tree_url = makeuri_contextless(
                            request,
                            [
                                ("mode", "bi_rule_tree"),
                                ("id", rule_id),
                                ("pack", self.bi_pack.id),
                            ],
                        )
                        html.icon_button(tree_url, _("This is a top-level rule. Show rule tree"),
                                         "bitree")

                    if refs == 0:
                        delete_url = make_confirm_link(
                            url=html.makeactionuri_contextless([("mode", "bi_rules"),
                                                                ("_del_rule", rule_id),
                                                                ("pack", self.bi_pack.id)]),
                            message=_("Do you really want to delete the rule with "
                                      "the ID <b>%s</b>?") % rule_id,
                        )
                        html.icon_button(delete_url, _("Delete this rule"), "delete")

                    table.cell("", css="narrow")
                    if bi_rule.computation_options.disabled:
                        html.icon("disabled",
                                  _("This rule is currently disabled and will not be applied"))
                    else:
                        html.empty_icon_button()

                    table.text_cell(_("Level"), level or "", css="number")
                    table.text_cell(_("ID"), html.render_a(rule_id, edit_url))
                    table.text_cell(_("Parameters"), " ".join(bi_rule.params.arguments))

                    if bi_rule.properties.icon:
                        title = html.render_icon(
                            bi_rule.properties.icon) + "&nbsp;" + bi_rule.properties.title
                    else:
                        title = bi_rule.properties.title
                    table.text_cell(_("Title"), title)

                    aggr_func_data = BIAggregationFunctionSchema().dump(
                        bi_rule.aggregation_function)
                    aggr_func_gui = bi_valuespecs.bi_config_aggregation_function_registry[
                        bi_rule.aggregation_function.type()]

                    table.text_cell(_("Aggregation Function"), str(aggr_func_gui(aggr_func_data)))
                    table.text_cell(_("Nodes"), bi_rule.num_nodes(), css="number")
                    table.cell(_("Used by"))
                    have_this = set([])
                    for (pack_id, aggr_id,
                         bi_aggregation) in aggregations_that_use_rule.get(rule_id, []):
                        if aggr_id not in have_this:
                            aggr_url = makeuri_contextless(
                                request,
                                [("mode", "bi_edit_aggregation"), ("id", aggr_id),
                                 ("pack", pack_id)],
                            )
                            html.a(self._aggregation_title(bi_aggregation), href=aggr_url)
                            html.br()
                            have_this.add(aggr_id)

                    table.text_cell(_("Comment"), bi_rule.properties.comment or "")
                    table.text_cell(_("Documentation URL"), bi_rule.properties.docu_url or "")

    def _aggregation_title(self, bi_aggregation):
        rule = self._bi_packs.get_rule(bi_aggregation.node.action.rule_id)
        assert rule is not None
        return "%s (%s)" % (rule.properties.title, rule.id)

    def _find_aggregation_rule_usages(self):
        aggregations_that_use_rule: Dict[str, List] = {}
        for pack_id, bi_pack in self._bi_packs.get_packs().items():
            for aggr_id, bi_aggregation in bi_pack.get_aggregations().items():
                action = bi_aggregation.node.action
                if not isinstance(action, BICallARuleAction):
                    continue

                rule_id = action.rule_id
                aggregations_that_use_rule.setdefault(rule_id, []).append(
                    (pack_id, aggr_id, bi_aggregation))
                sub_rule_ids = self._aggregation_recursive_sub_rule_ids(rule_id)
                for sub_rule_id in sub_rule_ids:
                    aggregations_that_use_rule.setdefault(sub_rule_id, []).append(
                        (pack_id, aggr_id, bi_aggregation))
        return aggregations_that_use_rule

    def _aggregation_recursive_sub_rule_ids(self, rule_id):
        bi_pack = self._bi_packs.get_pack_of_rule(rule_id)
        if bi_pack is None:
            return []

        bi_rule = bi_pack.get_rule(rule_id)
        sub_rule_ids = self._get_sub_rule_ids(bi_rule)
        if not sub_rule_ids:
            return []

        result = sub_rule_ids[:]
        for sub_rule_id in sub_rule_ids:
            result += self._aggregation_recursive_sub_rule_ids(sub_rule_id)
        return result

    def _get_sub_rule_ids(self, bi_rule):
        return [
            bi_node.action.rule_id
            for bi_node in bi_rule.get_nodes()
            if isinstance(bi_node.action, BICallARuleAction)
        ]


@mode_registry.register
class ModeBIEditRule(ABCBIMode):
    @classmethod
    def name(cls):
        return "bi_edit_rule"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        super().__init__()
        self._rule_id = html.request.get_str_input("id")
        self._new = self._rule_id is None

        if not self._new and self._rule_id is not None and not self.bi_pack.get_rule(self._rule_id):
            raise MKUserError("id", _("This BI rule does not exist"))

    @property
    def rule_id(self) -> str:
        assert self._rule_id is not None
        return self._rule_id

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeBIRules

    def title(self):
        if self._new:
            return _("Add BI Rule")
        return _("Edit Rule") + " " + escaping.escape_attribute(self._rule_id)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb,
                                          form_name="birule",
                                          button_name="_save",
                                          save_title=_("Create") if self._new else _("Save"),
                                          save_is_enabled=bi_valuespecs.is_contact_for_pack(
                                              self.bi_pack))

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return redirect(mode_url("bi_rules", pack=self.bi_pack.id))

        self.verify_pack_permission(self.bi_pack)
        vs_rule = self.valuespec(rule_id=self._rule_id)
        vs_rule_config = vs_rule.from_html_vars('rule')

        vs_rule.validate_value(copy.deepcopy(vs_rule_config), 'rule')
        new_bi_rule = BIRule(vs_rule_config)
        self._action_modify_rule(new_bi_rule)
        return redirect(mode_url("bi_rules", pack=self.bi_pack.id))

    def _action_modify_rule(self, new_bi_rule):
        if self._new:
            self._rule_id = new_bi_rule.id

        existing_bi_pack = self._bi_packs.get_pack_of_rule(self._rule_id) if self._rule_id else None
        if self._new and self._rule_id and existing_bi_pack is not None:
            existing_bi_rule = existing_bi_pack.get_rule(self._rule_id)
            assert existing_bi_rule is not None
            raise MKUserError(
                'rule_p_id',
                _("There is already a rule with the ID <b>%s</b>. "
                  "It is in the pack <b>%s</b> and as the title <b>%s</b>") %
                (self._rule_id, existing_bi_pack.title, existing_bi_rule.title))

        if new_bi_rule.num_nodes() == 0:
            raise MKUserError(None,
                              _("Please add at least one child node. Empty rules are useless."))

        self.bi_pack.add_rule(new_bi_rule)
        try:
            self._bi_packs.save_config()
        except MKGeneralException as e:
            raise MKUserError(None, str(e))

        if self._new:
            self._add_change("bi-new-rule", _("Add BI rule %s") % new_bi_rule.id)
        else:
            self._add_change("bi-edit-rule", _("Modified BI rule %s") % new_bi_rule.id)

    def _get_forbidden_packs_using_rule(self):
        forbidden_packs = set()
        for pack_id, bi_pack in self._bi_packs.get_packs().items():
            uses_rule = False
            if self.bi_pack.id == bi_pack.id:
                continue
            for rule_id, bi_rule in bi_pack.get_rules().items():
                if rule_id == self._rule_id:
                    uses_rule = True
                    break
                for bi_node in bi_rule.get_nodes():
                    action = bi_node.action
                    if isinstance(action, BICallARuleAction) and self._rule_id == action.rule_id:
                        uses_rule = True
                        break

            for aggregation in bi_pack.get_aggregations().values():
                action = aggregation.node.action
                if isinstance(action, BICallARuleAction) and self._rule_id == action.rule_id:
                    uses_rule = True
                    break
            if uses_rule and not bi_valuespecs.is_contact_for_pack(bi_pack):
                forbidden_packs.add(pack_id)
        return forbidden_packs

    def page(self):
        self.verify_pack_permission(self.bi_pack)

        if self._new:
            cloneid = html.request.var("clone")
            if cloneid is not None:
                try:
                    bi_rule = self.bi_pack.get_rule_mandatory(cloneid).clone()
                except KeyError:
                    raise MKGeneralException(_("This BI rule does not exist"))
            else:
                default_value = BIRuleSchema().dump({"pack_id": self.bi_pack.id})
                bi_rule = BIRule(default_value)
        else:
            bi_rule = self.bi_pack.get_rule_mandatory(self.rule_id)

        self._may_use_rules_from_packs(bi_rule)

        html.begin_form("birule", method="POST")
        rule_vs_config = BIRuleSchema().dump(bi_rule)
        self.valuespec(rule_id=self._rule_id).render_input("rule", rule_vs_config)
        forms.end()
        html.hidden_fields()
        if self._new:
            html.set_focus("rule_p_id")
        else:
            html.set_focus("rule_p_title")
        html.end_form()

        self._add_rule_arguments_lookup()

    def _may_use_rules_from_packs(self, bi_rule):
        rules_without_permissions: Dict[_Tuple[str, str], Any] = {}
        for bi_node in bi_rule.get_nodes():
            if bi_node.action.type() != 'call_a_rule':
                continue

            bi_pack = self._bi_packs.get_pack_of_rule(bi_rule.id)
            if bi_pack is not None and not bi_valuespecs.may_use_rules_in_pack(bi_pack):
                forbidden_pack = (bi_pack.id, bi_pack.title)
                rules_without_permissions.setdefault(forbidden_pack, [])
                rules_without_permissions[forbidden_pack].append(bi_rule.id)

        if rules_without_permissions:
            message = ", ".join([
                _("BI rules %s from BI pack '%s'") %
                (", ".join(["'%s'" % ruleid
                            for ruleid in ruleids]), title)
                for (_nodeid, title), ruleids in rules_without_permissions.items()
            ])
            raise MKAuthException(
                _("You have no permission for changes in this rule using %s.") % message)

    def _transform_back_vs_call_rule(self, choice):
        return choice[1]

    def _transform_forth_vs_call_rule(self, rule_id):
        bi_pack = self._bi_packs.get_rule(rule_id)
        if bi_pack:
            return (bi_pack.id, rule_id)
        return None

    @classmethod
    def valuespec(cls, rule_id: _Optional[str]):
        if rule_id:
            id_valuespec: ValueSpec = FixedValue(
                value=rule_id,
                title=_("Rule ID"),
            )
        else:
            id_valuespec = TextAscii(
                title=_("Rule ID"),
                help=_(
                    "The ID of the rule must be a unique text. It will be used as an internal key "
                    "when rules refer to each other. The rule IDs will not be visible in the status "
                    "GUI. They are just used within the configuration."),
                allow_empty=False,
                size=80,
            )

        elements = [
            ("id", id_valuespec),
            ("title",
             TextUnicode(
                 title=_("Rule Title"),
                 help=_("The title of the BI nodes which are created from this rule. This will be "
                        "displayed as the name of the node in the BI view. For "
                        "top level nodes this title must be unique. You can insert "
                        "rule parameters like <tt>$FOO$</tt> or <tt>$BAR$</tt> here."),
                 allow_empty=False,
                 size=80,
             )),
            ("comment",
             TextAreaUnicode(
                 title=_("Comment"),
                 help=_("An arbitrary comment of this rule for you."),
                 cols=80,
                 rows=4,
             )),
            ("docu_url",
             TextAscii(
                 title=_("Documentation URL"),
                 help=HTML(
                     _("An optional URL pointing to documentation or any other page. This will be "
                       "displayed as an icon %s and open "
                       "a new page when clicked. You can use either global URLs (beginning with "
                       "<tt>http://</tt>), absolute local urls (beginning with <tt>/</tt>) or relative "
                       "URLs (that are relative to <tt>check_mk/</tt>).") %
                     html.render_icon("url")),
                 size=80,
             )),
            ("params",
             Transform(
                 ListOfStrings(
                     title=_("Parameters"),
                     help=_(
                         "Parameters are used in order to make rules more flexible. They must "
                         "be named like variables in programming languages. For example you can "
                         "make your rule have the two parameters <tt>HOST</tt> and <tt>INST</tt>. "
                         "When calling the rule - from an aggergation or a higher level rule - "
                         "you can then specify two arbitrary values for these parameters. In the "
                         "title of the rule as well as the host and service names, you can insert the "
                         "actual value of the parameters by <tt>$HOST$</tt> and <tt>$INST$</tt> "
                         "(enclosed in dollar signs)."),
                     orientation="horizontal",
                     valuespec=TextAscii(
                         size=80,
                         regex='[A-Za-z_][A-Za-z0-9_]*',
                         regex_error=_("Parameters must contain only A-Z, a-z, 0-9 and _ "
                                       "and must not begin with a digit."),
                     )),
                 forth=lambda x: x["arguments"],
                 back=lambda x: {
                     "arguments": x,
                 },
             )),
            ("node_visualization",
             NodeVisualizationLayoutStyle(
                 title="BI visualization layout style",
                 help=_("The following layout style is applied to the matching node"))),
            ("icon", IconSelector(title=_("Icon"), with_emblem=False)),
            ("nodes",
             ListOf(
                 bi_valuespecs.get_bi_rule_node_choices_vs(),
                 add_label=_("Add child node generator"),
                 title=_("Nodes that are aggregated by this rule"),
             )),
            ("state_messages",
             Optional(
                 Dictionary(elements=[(state,
                                       TextAscii(
                                           title=_("Message when rule result is %s") % name,
                                           default_value=None,
                                           size=80,
                                       )) for state, name in [
                                           ("0", "OK"),
                                           ("1",
                                            "WARN"),
                                           ("2",
                                            "CRIT"),
                                           ("3",
                                            "UNKNOWN"),
                                       ]]),
                 title=_("Additional messages describing rule state"),
                 help=
                 _("This option allows you to display an additional, freely configurable text, to the rule outcome, "
                   "which may describe the state more in detail. For example, instead of <tt>CRIT</tt>, the rule can now "
                   "display <tt>CRIT, less than 70% of servers reachable</tt>. This message is also shown within the BI aggregation "
                   "check plugins."),
                 label=_("Add messages"))),
            ("disabled",
             Checkbox(
                 title=_("Rule activation"),
                 help=_("Disabled rules are kept in the configuration but are not applied."),
                 label=_("do not apply this rule"),
             )),
            ("aggregation_function", bi_valuespecs.get_aggregation_function_choices()),
        ]

        def convert_to_vs(value):
            for what in ["title", "state_messages", "docu_url", "icon", "comment"]:
                value[what] = value["properties"].pop(what)
            value["disabled"] = value["computation_options"].pop("disabled")

            del value["properties"]
            del value["computation_options"]
            return value

        def convert_from_vs(value):
            value["properties"] = {}
            for what in ["title", "docu_url", "icon", "comment"]:
                value["properties"][what] = value.pop(what) or ""

            for what in ["state_messages"]:
                value["properties"][what] = value.get(what, {})

            value["computation_options"] = {}
            value["computation_options"]["disabled"] = value.pop("disabled")
            return value

        return Transform(
            BIRuleForm(title=_("Rule Properties"),
                       optional_keys=False,
                       render="form",
                       elements=elements,
                       headers=[
                           (_("Rule Properties"), [
                               "id", "title", "docu_url", "comment", "params", "node_visualization",
                               "state_messages", "icon", "disabled"
                           ]),
                           (_("Child Node Generation"), ["nodes"]),
                           (_("Aggregation Function"), ["aggregation_function"]),
                       ]),
            forth=convert_to_vs,
            back=convert_from_vs,
        )


class BIRuleForm(Dictionary):
    def render_input(self, varprefix, value):
        super().render_input(varprefix, value)
        html.javascript("new cmk.bi.BIRulePreview('#form_birule', '%s')" % (varprefix))


class BIAggregationForm(Dictionary):
    def render_input(self, varprefix, value):
        super().render_input(varprefix, value)
        html.javascript("new cmk.bi.BIAggregationPreview('#form_biaggr', '%s')" % (varprefix))


@page_registry.register_page("ajax_bi_rule_preview")
class AjaxBIRulePreview(AjaxPage):
    def page(self):
        sites_callback = SitesCallback(cmk.gui.sites.states, bi_livestatus_query)
        compiler = BICompiler(BIManager.bi_configuration_file(), sites_callback)
        compiler.prepare_for_compilation(compiler.compute_current_configstatus()["online_sites"])

        # Create preview rule
        vs = ModeBIEditRule.valuespec(rule_id=None)
        varprefix = html.request.var("varprefix")
        preview_config = vs.from_html_vars(varprefix)
        preview_bi_rule = BIRule(preview_config)

        mapped_example_arguments = {}
        example_arguments = json.loads(html.request.get_str_input_mandatory("example_arguments"))
        for idx, name in enumerate(preview_bi_rule.params.arguments):
            if idx >= len(example_arguments):
                break
            mapped_example_arguments["$%s$" % name] = example_arguments[idx]

        response = []
        for node in preview_bi_rule.nodes:
            try:
                # TODO: start in thread, check timeout
                # Provide performance statistics/advice for bad regex and setups
                search_results = node.search.execute(mapped_example_arguments, compiler.bi_searcher)
                modified_search_results = []
                for search_result in search_results:
                    entry = mapped_example_arguments.copy()
                    entry.update(search_result)
                    modified_search_results.append(entry)
                response.append(_finalize_preview_response(modified_search_results))
            except MKGeneralException:
                response.append([{"Error": _("Can not evaluate search")}])

        return {
            "title": _("Search result(s) preview"),
            "data": response,
            "params": preview_bi_rule.params.arguments,
        }


@page_registry.register_page("ajax_bi_aggregation_preview")
class AjaxBIAggregationPreview(AjaxPage):
    def page(self):
        # Prepare compiler
        sites_callback = SitesCallback(cmk.gui.sites.states, bi_livestatus_query)
        compiler = BICompiler(BIManager.bi_configuration_file(), sites_callback)
        compiler.prepare_for_compilation(compiler.compute_current_configstatus()["online_sites"])

        # Create preview aggr
        varprefix = html.request.var("varprefix")
        vs = BIModeEditAggregation.get_vs_aggregation(aggregation_id=None)
        preview_config = vs.from_html_vars(varprefix)
        preview_bi_aggr = BIAggregation(preview_config)

        response = []
        try:
            # TODO: start in thread, check timeout
            # Provide performance statistics/advice for bad regex and setups
            search_results = preview_bi_aggr.node.search.execute({}, compiler.bi_searcher)
            response.append(_finalize_preview_response(search_results))
        except MKGeneralException:
            response.append([{_("Error"): _("Can not evaluate search")}])

        return {
            "title": _("Search result(s) preview"),
            "data": response,
        }


def _finalize_preview_response(response):
    if len(response) == 0:
        return [{_("No matches"): ""}]
    if len(response) == 1 and response[0] == {}:
        return [{_("One match without arguments"): ""}]
    return response


class NodeVisualizationLayoutStyle(ValueSpec):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._style_type = kwargs.get("type", "hierarchy")

    def render_input(self, varprefix, value):
        html.div("", id_=varprefix)
        html.javascript(
            "let example = new cmk.node_visualization_layout_styles.LayoutStyleExampleGenerator(%s);"
            "example.create_example(%s)" % (json.dumps(varprefix), json.dumps(value)))

    def value_to_text(self, value):
        return ""

    def from_html_vars(self, varprefix):
        value = self.default_value()
        for key, val in html.request.itervars():
            if key.startswith(varprefix):
                clean_key = key[len(varprefix):]
                if clean_key == "type":
                    value[clean_key] = val
                elif clean_key.startswith("_type_value_"):
                    value["style_config"][clean_key[12:]] = int(val)
                elif clean_key.startswith("_type_checkbox_"):
                    value["style_config"][clean_key[15:]] = val == "on"
        return value

    def default_value(self):
        return {"type": "none", "style_config": {}}


#.
#   .--Edit Aggregation----------------------------------------------------.
#   |                          _____    _ _ _                              |
#   |                         | ____|__| (_) |_                            |
#   |                         |  _| / _` | | __|                           |
#   |                         | |__| (_| | | |_                            |
#   |                         |_____\__,_|_|\__|                           |
#   |                                                                      |
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   '----------------------------------------------------------------------'


@mode_registry.register
class BIModeEditAggregation(ABCBIMode):
    @classmethod
    def name(cls):
        return "bi_edit_aggregation"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        super().__init__()
        aggr_id = html.request.get_str_input_mandatory("id", "")
        clone_id = html.request.get_str_input_mandatory("clone", "")
        self._new = False
        self._clone = False
        if clone_id:
            self._clone = True
            try:
                bi_aggregation = self.bi_pack.get_aggregation_mandatory(clone_id)
                self._bi_aggregation = bi_aggregation.clone()
                self._bi_aggregation.id = ""
            except KeyError:
                raise MKUserError("id", _("This BI aggregation does not exist"))
        elif aggr_id == "":
            self._new = True
            self._bi_aggregation = BIAggregation()
            self._bi_aggregation.pack_id = self.bi_pack.id
        else:
            try:
                self._bi_aggregation = self._bi_packs.get_aggregation_mandatory(aggr_id)
            except KeyError:
                raise MKUserError("id", _("This aggregation does not exist."))

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeBIPacks

    def title(self):
        if self._clone:
            return _("Clone Aggregation %s") % html.request.get_str_input_mandatory("clone")
        if self._new:
            return _("Add Aggregation")
        return _("Edit Aggregation")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb,
                                          form_name="biaggr",
                                          button_name="_save",
                                          save_is_enabled=bi_valuespecs.is_contact_for_pack(
                                              self.bi_pack))

    def _get_aggregations_by_id(self):
        ids = {}
        for bi_pack in self._bi_packs.get_packs().values():
            for bi_aggregation in bi_pack.get_aggregations().values():
                ids[bi_aggregation.id] = (bi_pack, bi_aggregation)
        return ids

    def action(self) -> ActionResult:
        self.verify_pack_permission(self.bi_pack)
        if not html.check_transaction():
            return redirect(mode_url("bi_aggregations", pack=self.bi_pack.id))

        vs_aggregation = self.get_vs_aggregation(aggregation_id=self._bi_aggregation.id)
        vs_aggregation_config = vs_aggregation.from_html_vars('aggr')
        vs_aggregation.validate_value(vs_aggregation_config, 'aggr')

        new_bi_aggregation = BIAggregation(vs_aggregation_config)

        if new_bi_aggregation.groups.count() == 0:
            raise MKUserError('rule_p_groups_0', _("Please define at least one aggregation group"))

        aggregation_ids = self._get_aggregations_by_id()
        if new_bi_aggregation.id in aggregation_ids and aggregation_ids[
                new_bi_aggregation.id][1].id != self._bi_aggregation.id:
            raise MKUserError(
                "aggr_p_id", "This aggregation id is already used in pack %s" %
                aggregation_ids[new_bi_aggregation.id][0].id)

        if self._clone and new_bi_aggregation.id in aggregation_ids:
            raise MKUserError(
                "aggr_p_id", "This aggregation id is already used in pack %s" %
                aggregation_ids[new_bi_aggregation.id][0].id)

        self.bi_pack.add_aggregation(new_bi_aggregation)
        self._bi_packs.save_config()
        if self._new:
            self._add_change("bi-new-aggregation",
                             _("Add new BI aggregation %s") % new_bi_aggregation.id)
        else:
            self._add_change("bi-edit-aggregation",
                             _("Modified BI aggregation %s") % (new_bi_aggregation.id))
        return redirect(mode_url("bi_aggregations", pack=self.bi_pack.id))

    def page(self):
        html.begin_form("biaggr", method="POST")

        aggr_vs_config = BIAggregationSchema().dump(self._bi_aggregation)
        self.get_vs_aggregation(aggregation_id=self._bi_aggregation.id).render_input(
            "aggr", aggr_vs_config)
        forms.end()
        html.hidden_fields()
        html.set_focus("aggr_p_groups_0")
        html.end_form()

        self._add_rule_arguments_lookup()

    @classmethod
    def get_vs_aggregation(cls, aggregation_id: _Optional[str]):
        if cmk_version.is_managed_edition():
            cme_elements = managed.customer_choice_element()
        else:
            cme_elements = []

        visualization_choices = []
        visualization_choices.append((None, _("Use default layout")))
        templates = BILayoutManagement.get_all_bi_template_layouts()
        for template_id in sorted(templates.keys()):
            visualization_choices.append((template_id, template_id))

        if aggregation_id:
            id_valuespec: ValueSpec = FixedValue(
                value=aggregation_id,
                title=_("Aggregation ID"),
            )
        else:
            id_valuespec = TextAscii(
                title=_("Aggregation ID"),
                help=_("The ID of the aggregation must be a unique text. It will be as unique ID."),
                allow_empty=False,
                size=80,
            )

        return BIAggregationForm(
            title=_("Aggregation Properties"),
            optional_keys=False,
            render="form",
            elements=cme_elements + [
                ("id", id_valuespec),
                ("groups", cls._get_vs_aggregation_groups()),
                ("node", bi_valuespecs.get_bi_aggregation_node_choices()),
                ("computation_options", cls._get_vs_computation_options()),
                ("aggregation_visualization", cls._get_vs_aggregation_visualization()),
            ])

    @classmethod
    def _get_vs_aggregation_groups(cls):
        def convert_to_vs(value):
            return value.get("names", []) + value.get("paths", [])

        def convert_from_vs(value):
            result = {}
            result["names"] = [x for x in value if not isinstance(x, list)]
            result["paths"] = [x for x in value if isinstance(x, list)]
            return result

        return Transform(
            ListOf(
                Alternative(
                    style="dropdown",
                    orientation="horizontal",
                    elements=[
                        TextUnicode(title=_("Group name")),
                        ListOfStrings(title=_("Group path"),
                                      orientation="horizontal",
                                      separator="/"),
                    ],
                ),
                default_value={},
                title=_("Aggregation Groups"),
            ),
            forth=convert_to_vs,
            back=convert_from_vs,
        )

    @classmethod
    def _get_vs_computation_options(cls):
        return Dictionary(
            elements=[
                ("disabled",
                 Checkbox(
                     title=_("Disabled"),
                     label=_("Currently disable this aggregation"),
                 )),
                ("use_hard_states",
                 Checkbox(
                     title=_("Use Hard States"),
                     label=_("Base state computation on hard states"),
                     help=
                     _("Hard states can only differ from soft states if at least one host or service "
                       "of the BI aggregate has more than 1 maximum check attempt. For example if you "
                       "set the maximum check attempts of a service to 3 and the service is CRIT "
                       "just since one check then it's soft state is CRIT, but its hard state is still OK. "
                       "<b>Note:</b> When computing the availbility of a BI aggregate this option "
                       "has no impact. For that purpose always the soft (i.e. real) states will be used."
                      ),
                 )),
                ("escalate_downtimes_as_warn",
                 Checkbox(
                     title=_("Aggregation of Downtimes"),
                     label=_("Escalate downtimes based on aggregated WARN state"),
                     help=
                     _("When computing the state 'in scheduled downtime' for an aggregate "
                       "first all leaf nodes that are within downtime are assumed CRIT and all others "
                       "OK. Then each aggregated node is assumed to be in downtime if the state "
                       "is CRIT under this assumption. You can change this to WARN. The influence of "
                       "this setting is especially relevant if you use aggregation functions of type <i>count</i> "
                       "and want the downtime information also escalated in case such a node would go into "
                       "WARN state."),
                 )),
            ],
            title=_("Computation options"),
            optional_keys=[],
        )

    @classmethod
    def _get_vs_aggregation_visualization(cls):
        return Dictionary(
            title=_("BI Visualization"),
            elements=[
                (
                    "layout_id",
                    DropdownChoice(
                        title=_("Base layout"),
                        choices=[
                            ("builtin_default", _("Default (%s)") %
                             config.default_bi_layout["node_style"][8:].title()),
                            ("builtin_force", _("Builtin: Force")),
                            ("builtin_hierarchy", _("Builtin: Hierarchy")),
                            ("builtin_radial", _("Builtin: Radial")),
                            # TODO: continue this list with user configurable layouts
                        ],
                        default_value="builtin_default")),
                ("line_style",
                 DropdownChoice(title=_("Style of connection lines"),
                                choices=[
                                    ("default", _("Default (%s)") %
                                     config.default_bi_layout["line_style"].title()),
                                    ("straight", "Straight"),
                                    ("round", _("Round")),
                                    ("elbow", _("Elbow")),
                                ],
                                default_value="round")),
                ("ignore_rule_styles",
                 Checkbox(title=_("Ignore styles specified in rules"), default_value=False)),
            ],
            optional_keys=[],
        )


#.
#   .--Aggregations--------------------------------------------------------.
#   |       _                                    _   _                     |
#   |      / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __  ___     |
#   |     / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \/ __|    |
#   |    / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | \__ \    |
#   |   /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|___/    |
#   |           |___/ |___/          |___/                                 |
#   '----------------------------------------------------------------------'


@mode_registry.register
class BIModeAggregations(ABCBIMode):
    @classmethod
    def name(cls):
        return "bi_aggregations"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeBIPacks

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, pack: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _breadcrumb_url(self) -> str:
        return self.mode_url(pack=self.bi_pack.id)

    def title(self):
        return self.title_for_pack(self.bi_pack) + " - " + _("Aggregations")

    def have_rules(self):
        return sum(x.num_rules() for x in self._bi_packs.get_packs().values()) > 0

    def action(self) -> ActionResult:
        self.verify_pack_permission(self.bi_pack)
        if not html.check_transaction():
            return redirect(self.mode_url(pack=self.bi_pack.id))

        if html.request.var("_del_aggr"):
            self._delete_after_confirm()

        elif html.request.var("_bulk_delete_bi_aggregations"):
            self._bulk_delete_after_confirm()

        elif html.request.var("_bulk_move_bi_aggregations"):
            self._bulk_move_after_confirm()

        return redirect(self.mode_url(pack=self.bi_pack.id))

    def _delete_after_confirm(self) -> None:
        aggregation_id = html.request.get_str_input_mandatory("_del_aggr")
        self._bi_packs.delete_aggregation(aggregation_id)
        self._add_change("bi-delete-aggregation", _("Deleted BI aggregation %s") % (aggregation_id))
        self._bi_packs.save_config()

    def _bulk_delete_after_confirm(self) -> None:
        selection = sorted(map(str, self._get_selection("aggregation")))
        if not selection:
            return

        for aggregation_id in selection[::-1]:
            self._bi_packs.delete_aggregation(aggregation_id)
            self._add_change("bi-delete-aggregation",
                             _("Deleted BI aggregation with ID %s") % (aggregation_id))
        self._bi_packs.save_config()

    def _bulk_move_after_confirm(self) -> None:
        target = None
        if html.request.has_var('bulk_moveto'):
            target = html.request.var('bulk_moveto', '')
            html.javascript('cmk.selection.update_bulk_moveto("%s")' % target)

        target_pack = None
        if target in self._bi_packs.get_packs():
            target_pack = self._bi_packs.get_pack(target)
            self.verify_pack_permission(target_pack)

        selection = list(map(str, self._get_selection("aggregation")))
        if not selection or target_pack is None:
            return None

        for aggregation_id in selection[::-1]:
            bi_aggregation = self.bi_pack.get_aggregation_mandatory(aggregation_id)
            self._bi_packs.delete_aggregation(aggregation_id)
            target_pack.add_aggregation(bi_aggregation)
            self._add_change(
                "bi-move-aggregation",
                _("Moved BI aggregation with ID %s to BI pack %s") % (aggregation_id, target))
        self._bi_packs.save_config()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        aggr_entries = []
        if self.have_rules() and bi_valuespecs.is_contact_for_pack(self.bi_pack):
            aggr_entries.append(
                PageMenuEntry(
                    title=_("Add aggregation"),
                    icon_name="new",
                    item=make_simple_link(
                        self.url_to_pack([("mode", "bi_edit_aggregation")], self.bi_pack)),
                    is_shortcut=True,
                    is_suggested=True,
                ))

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="aggregations",
                    title=_("Aggregations"),
                    topics=[
                        PageMenuTopic(
                            title=_("In this pack"),
                            entries=aggr_entries,
                        ),
                        PageMenuTopic(
                            title=_("On selected aggregations"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Delete aggregations"),
                                    icon_name="delete",
                                    item=make_confirmed_form_submit_link(
                                        form_name="bulk_action_form",
                                        button_name="_bulk_delete_bi_aggregations",
                                        message=_(
                                            "Do you really want to delete the selected aggregations?"
                                        ),
                                    ),
                                    is_enabled=bool(self.bi_pack and
                                                    self.bi_pack.num_aggregations() > 0),
                                ),
                                PageMenuEntry(
                                    title=_("Move aggregations"),
                                    icon_name="move",
                                    name="move_aggregations",
                                    item=PageMenuPopup(self._render_bulk_move_form()),
                                    is_enabled=bool(self.bi_pack and
                                                    self.bi_pack.num_aggregations() > 0 and
                                                    self._show_bulk_move_choices()),
                                ),
                            ],
                        ),
                        make_checkbox_selection_topic(),
                    ],
                ),
                PageMenuDropdown(
                    name="rules",
                    title=_("Rules"),
                    topics=[
                        PageMenuTopic(
                            title=_("In this pack"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Rules"),
                                    icon_name="bi_rules",
                                    item=make_simple_link(
                                        self.url_to_pack([("mode", "bi_rules")], self.bi_pack),),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def page(self):
        html.begin_form("bulk_action_form", method="POST")
        self._render_aggregations()
        html.hidden_fields()
        html.end_form()

    def _render_bulk_move_form(self) -> str:
        with html.plugged():
            move_choices = self._show_bulk_move_choices()
            if not move_choices:
                return ""

            if html.request.has_var('bulk_moveto'):
                html.javascript('cmk.selection.update_bulk_moveto("%s")' %
                                html.request.var('bulk_moveto', ''))

            html.add_confirm_on_submit("bulk_action_form",
                                       _("Do you really want to move the selected aggregations?"))

            html.dropdown(
                "bulk_moveto",
                move_choices,
                "@",
                onchange="cmk.selection.update_bulk_moveto(this.value)",
                class_='bulk_moveto',
                label=_("Move to pack: "),
                form="form_bulk_action_form",
            )

            html.button("_bulk_move_bi_aggregations",
                        _("Bulk move"),
                        "submit",
                        form="form_bulk_action_form")
            return html.drain()

    def _show_bulk_move_choices(self) -> Choices:
        return [(pack_id, bi_pack.title)
                for pack_id, bi_pack in self._bi_packs.get_packs().items()
                if pack_id is not self.bi_pack.id and bi_valuespecs.is_contact_for_pack(bi_pack)]

    def _render_aggregations(self):
        with table_element("bi_aggr", _("Aggregations")) as table:
            for aggregation_id, bi_aggregation in self.bi_pack.get_aggregations().items():
                table.row()
                table.cell(html.render_input("_toggle_group",
                                             type_="button",
                                             class_="checkgroup",
                                             onclick="cmk.selection.toggle_all_rows();",
                                             value='X'),
                           sortable=False,
                           css="checkbox")
                html.checkbox("_c_aggregation_%s" % aggregation_id)

                table.cell(_("Actions"), css="buttons")
                edit_url = makeuri_contextless(
                    request,
                    [("mode", "bi_edit_aggregation"), ("id", aggregation_id),
                     ("pack", self.bi_pack.id)],
                )
                html.icon_button(edit_url, _("Edit this aggregation"), "edit")

                clone_url = self.url_to_pack([("mode", "bi_edit_aggregation"),
                                              ("clone", bi_aggregation.id)], self.bi_pack)
                html.icon_button(clone_url, _("Create a copy of this aggregation"), "clone")

                if bi_valuespecs.is_contact_for_pack(self.bi_pack):
                    delete_url = make_confirm_link(
                        url=html.makeactionuri([("_del_aggr", aggregation_id)]),
                        message=_("Do you really want to delete the aggregation <b>%s</b>?") %
                        (aggregation_id),
                    )
                    html.icon_button(delete_url, _("Delete this aggregation"), "delete")

                table.text_cell(_("ID"), aggregation_id)

                if cmk_version.is_managed_edition():
                    table.text_cell(_("Customer"))
                    if bi_aggregation.customer:
                        html.write_text(managed.get_customer_name_by_id(bi_aggregation.customer))

                table.text_cell(_("Options"), css="buttons")

                if bi_aggregation.computation_options.disabled:
                    html.icon("disabled", _("This aggregation is currently disabled."))
                else:
                    html.icon("enabled", _("This aggregation is currently enabled."))

                if bi_aggregation.computation_options.use_hard_states:
                    html.icon("hard_states", _("Base state computation on hard states"))
                else:
                    html.icon("all_states", _("Base state computation on soft and hard states"))

                if bi_aggregation.computation_options.escalate_downtimes_as_warn:
                    html.icon("warning", _("Escalate downtimes based on aggregated WARN state"))
                else:
                    html.icon("critical", _("Escalate downtimes based on aggregated CRIT state"))

                table.text_cell(_("Groups"), ", ".join(bi_aggregation.groups.names))
                table.text_cell(_("Paths"),
                                ", ".join(["/".join(x) for x in bi_aggregation.groups.paths]))

                action = bi_aggregation.node.action
                assert isinstance(action, BICallARuleAction)
                rule_id = action.rule_id
                edit_url = makeuri(
                    request,
                    [("mode", "bi_edit_rule"), ("pack", self.bi_pack.id), ("id", rule_id)],
                )
                table.cell(_("Rule Tree"), css="bi_rule_tree")
                self.render_aggregation_rule_tree(bi_aggregation)

    def render_aggregation_rule_tree(self, bi_aggregation):
        toplevel_rule = self._bi_packs.get_rule(bi_aggregation.node.action.rule_id)
        if not toplevel_rule:
            html.show_error(_("The top level rule does not exist."))
            return
        self.render_rule_tree(toplevel_rule.id,
                              toplevel_rule.id,
                              tree_prefix="%s_" % bi_aggregation.id)


#.
#   .--Rule Tree-----------------------------------------------------------.
#   |               ____        _        _____                             |
#   |              |  _ \ _   _| | ___  |_   _| __ ___  ___                |
#   |              | |_) | | | | |/ _ \   | || '__/ _ \/ _ \               |
#   |              |  _ <| |_| | |  __/   | || | |  __/  __/               |
#   |              |_| \_\\__,_|_|\___|   |_||_|  \___|\___|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIRuleTree(ABCBIMode):
    @classmethod
    def name(cls):
        return "bi_rule_tree"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeBIPacks

    def __init__(self):
        super().__init__()
        self._rule_id = html.request.get_str_input_mandatory("id")
        self._rule_tree_bi_pack = self._bi_packs.get_pack_of_rule(self._rule_id)
        if not self._rule_tree_bi_pack:
            raise MKUserError("id", _("This BI rule does not exist"))

    def title(self):
        return self.title_for_pack(
            self._rule_tree_bi_pack) + _("Rule tree of") + " " + self._rule_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb)

    def page(self):
        _aggr_refs, rule_refs, _level = self._bi_packs.count_rule_references(self._rule_id)
        if rule_refs == 0:
            with table_element(sortable=False, searchable=False) as table:
                table.row()
                table.cell(_("Rule Tree"), css="bi_rule_tree")
                self.render_rule_tree(self._rule_id, self._rule_id)


#   .--WATO Permissions----------------------------------------------------.
#   |                     __        ___  _____ ___                         |
#   |                     \ \      / / \|_   _/ _ \                        |
#   |                      \ \ /\ / / _ \ | || | | |                       |
#   |                       \ V  V / ___ \| || |_| |                       |
#   |                        \_/\_/_/   \_\_| \___/                        |
#   |                                                                      |
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

permission_registry.register(
    Permission(
        section=PermissionSectionWATO,
        name="bi_rules",
        title=_l("Business Intelligence Rules and Aggregations"),
        description=_l("Use the WATO BI module, create, modify and delete BI rules and "
                       "aggregations in packs that you are a contact of."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=PermissionSectionWATO,
        name="bi_admin",
        title=_l("Business Intelligence Administration"),
        description=_l("Edit all rules and aggregations for Business Intelligence, "
                       "create, modify and delete rule packs."),
        defaults=["admin"],
    ))
