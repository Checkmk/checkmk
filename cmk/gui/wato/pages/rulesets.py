#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO's awesome rule editor: Lets the user edit rule based parameters"""

import abc
import itertools
import pprint
import re
import json
from enum import Enum, auto
from typing import Dict, Generator, List, Optional, Union, Any, Iterable, Type

from six import ensure_str

from cmk.utils.regex import escape_regex_chars
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
from cmk.utils.type_defs import (
    HostNameConditions,
    ServiceNameConditions,
    HostName,
    ServiceName,
)

from cmk.gui.type_defs import HTTPVariables
import cmk.gui.escaping as escaping
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.view_utils
from cmk.gui.table import table_element
import cmk.gui.forms as forms
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError, MKAuthException
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Transform,
    Checkbox,
    ListChoice,
    Tuple,
    ListOfStrings,
    Dictionary,
    RegExpUnicode,
    DropdownChoice,
    rule_option_elements,
)
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuSearch,
    make_display_options_dropdown,
    make_simple_link,
    make_form_submit_link,
    make_simple_form_page_menu,
)
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.gui.watolib.rulesets import RuleConditions
from cmk.gui.watolib.rulespecs import (
    rulespec_group_registry,
    rulespec_registry,
    Rulespec,
)
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.plugins.wato.utils.main_menu import main_module_registry
from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    wato_confirm,
    make_action_link,
    add_change,
    may_edit_ruleset,
    search_form,
    ConfigHostname,
    HostTagCondition,
    DictHostTagCondition,
)

from cmk.gui.plugins.wato.utils import LabelCondition

if watolib.has_agent_bakery():
    import cmk.gui.cee.plugins.wato.agent_bakery.misc as agent_bakery  # pylint: disable=import-error,no-name-in-module
else:
    agent_bakery = None  # type: ignore[assignment]

SearchOptions = Dict[str, Any]


def render_html(text: Union[HTML, str]) -> str:
    if isinstance(text, HTML):
        return text.__html__()
    return text


class PageType(Enum):
    DeprecatedRulesets = auto()
    IneffectiveRules = auto()
    UsedRulesets = auto()
    RulesetGroup = auto()
    RuleSearch = auto()


class ABCRulesetMode(WatoMode):
    """Lists rulesets in their groups.

    Besides the simple listing, it is also responsible for displaying rule search results.
    """
    def __init__(self) -> None:
        super(ABCRulesetMode, self).__init__()
        self._page_type = self._get_page_type(self._search_options)

        self._title: str = ""
        self._help: Optional[str] = None
        self._set_title_and_help()

    @abc.abstractmethod
    def _set_title_and_help(self):
        raise NotImplementedError()

    def _from_vars(self):

        #  Explicitly hide deprecated rulesets by default
        if not html.request.has_var("search_p_ruleset_deprecated"):
            html.request.set_var("search_p_ruleset_deprecated", DropdownChoice.option_id(False))
            html.request.set_var("search_p_ruleset_deprecated_USE", "on")

        # Transform group argument to the "rule search arguments"
        # Keeping this for compatibility reasons for the moment
        # This is either given via "group" parameter or via search (see blow)
        if html.request.has_var("group"):
            group_name = html.request.get_ascii_input_mandatory("group")
            html.request.set_var("search_p_ruleset_group", DropdownChoice.option_id(group_name))
            html.request.set_var("search_p_ruleset_group_USE", "on")
            html.request.del_var("group")

        self._group_name: Optional[str] = None
        if html.request.has_var("search_p_ruleset_group"):
            self._group_name = _vs_ruleset_group(
                self.name()).from_html_vars("search_p_ruleset_group")

        # Transform the search argument to the "rule search" arguments
        if html.request.has_var("search"):
            html.request.set_var("search_p_fulltext",
                                 html.request.get_unicode_input_mandatory("search"))
            html.request.set_var("search_p_fulltext_USE", "on")
            html.request.del_var("search")

        # Transform the folder argumen (from URL or bradcrumb) to the "rule search arguments
        if html.request.var("folder"):
            html.request.set_var("search_p_rule_folder_0",
                                 DropdownChoice.option_id(html.request.var("folder")))
            html.request.set_var("search_p_rule_folder_1", DropdownChoice.option_id(True))
            html.request.set_var("search_p_rule_folder_USE", "on")

        self._search_options: SearchOptions = ModeRuleSearchForm().search_options

    @abc.abstractmethod
    def _get_page_type(self, search_options: SearchOptions) -> PageType:
        raise NotImplementedError()

    @abc.abstractmethod
    def _rulesets(self):
        raise NotImplementedError()

    def title(self):
        return self._title

    def page(self):
        if self._help:
            html.help(self._help)

        rulesets = self._rulesets()
        rulesets.load()

        # In case the user has filled in the search form, filter the rulesets by the given query
        if self._search_options:
            rulesets = watolib.SearchedRulesets(rulesets, self._search_options)

        if self._page_type is PageType.RuleSearch and not html.form_submitted():
            return  # Do not show the result list when no query has been made

        html.open_div(class_="rulesets")

        grouped_rulesets = sorted(rulesets.get_grouped(),
                                  key=lambda k_v: watolib.get_rulegroup(k_v[0]).title)

        for main_group_name, sub_groups in grouped_rulesets:
            # Display the main group header only when there are several main groups shown
            if len(grouped_rulesets) > 1:
                html.h3(watolib.get_rulegroup(main_group_name).title)
                html.br()

            for group_name, group_rulesets in sub_groups:
                forms.header(watolib.get_rulegroup(group_name).title)
                forms.container()

                for ruleset in group_rulesets:
                    float_cls = None
                    if not config.wato_hide_help_in_lists:
                        float_cls = "nofloat" if config.user.show_help else "float"
                    html.open_div(class_=["ruleset", float_cls],
                                  title=escaping.strip_tags(ruleset.help() or ''))
                    html.open_div(class_="text")

                    url_vars = [
                        ("mode", "edit_ruleset"),
                        ("varname", ruleset.name),
                        ("back_mode", self.name()),
                    ]
                    view_url = html.makeuri(url_vars)

                    html.a(ruleset.title(),
                           href=view_url,
                           class_="nonzero" if ruleset.is_empty() else "zero")
                    html.span("." * 200, class_="dots")
                    html.close_div()

                    num_rules = ruleset.num_rules()
                    if ruleset.search_matching_rules:
                        num_rules_txt = "%d/%d" % (len(ruleset.search_matching_rules), num_rules)
                    else:
                        num_rules_txt = "%d" % num_rules

                    html.div(num_rules_txt,
                             class_=["rulecount", "nonzero" if ruleset.is_empty() else "zero"])
                    if not config.wato_hide_help_in_lists and ruleset.help():
                        html.help(ruleset.help())

                    html.close_div()
                forms.end()

        if not grouped_rulesets:
            if self._search_options:
                msg = _("There are no rulesets or rules matching your search.")
            else:
                msg = _("There are no rules defined in this folder.")

            html.div(msg, class_="info")

        html.close_div()


@mode_registry.register
class ModeRuleSearch(ABCRulesetMode):
    @classmethod
    def name(cls):
        return "rule_search"

    @classmethod
    def permissions(cls):
        return ["rulesets"]

    def _get_page_type(self, search_options: Dict[str, str]) -> PageType:
        if _is_deprecated_rulesets_page(search_options):
            return PageType.DeprecatedRulesets

        if _is_ineffective_rules_page(search_options):
            return PageType.IneffectiveRules

        if _is_used_rulesets_page(search_options):
            return PageType.UsedRulesets

        return PageType.RuleSearch

    def _rulesets(self):
        return watolib.NonStaticChecksRulesets()

    def _set_title_and_help(self):
        if self._page_type is PageType.DeprecatedRulesets:
            self._title = _("Search rules: Deprecated Rulesets")
            self._help = _(
                "Here you can see a list of all deprecated rulesets (which are not used by Check_MK anymore). If "
                "you have defined some rules here, you might have to migrate the rules to their successors. Please "
                "refer to the release notes or context help of the rulesets for details.")

        elif self._page_type is PageType.IneffectiveRules:
            self._title = _("Search rules: Rulesets with ineffective rules")
            self._help = _(
                "The following rulesets contain rules that do not match to any of the existing hosts."
            )

        elif self._page_type is PageType.UsedRulesets:
            self._title = _("Search rules: Used rulesets")
            self._help = _("Non-empty rulesets")

        elif self._page_type is PageType.RuleSearch:
            self._title = _("Search rules")
            self._help = None

        else:
            raise NotImplementedError()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rules",
                    title=_("Rules"),
                    topics=[
                        PageMenuTopic(
                            title=_("Detailed search"),
                            entries=[
                                _page_menu_entry_search_rules(self._search_options,
                                                              mode=self.name(),
                                                              page_type=self._page_type),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Predefined searches"),
                            entries=list(_page_menu_entries_predefined_searches()),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield _page_menu_entry_predefined_conditions()

    def page(self):
        # When the detailed search form is involved, don't show the quick search field on the result
        # page
        if not html.form_submitted("rule_search"):
            search_form(title="%s: " % _("Quick search"),
                        default_value=self._search_options.get("fulltext", ""))
        super().page()


def _page_menu_entries_predefined_searches() -> Iterable[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Used rulesets"),
        icon_name="usedrulesets",
        item=make_simple_link(
            watolib.folder_preserving_link([
                ("mode", "rule_search"),
                ("search_p_ruleset_used", DropdownChoice.option_id(True)),
                ("search_p_ruleset_used_USE", "on"),
            ])),
    )

    yield PageMenuEntry(
        title=_("Ineffective rules"),
        icon_name="rulesets_ineffective",
        item=make_simple_link(
            watolib.folder_preserving_link([
                ("mode", "rule_search"),
                ("search_p_rule_ineffective", DropdownChoice.option_id(True)),
                ("search_p_rule_ineffective_USE", "on"),
            ])),
    )

    yield PageMenuEntry(
        title=_("Deprecated rulesets"),
        icon_name="rulesets_deprecated",
        item=make_simple_link(
            watolib.folder_preserving_link([
                ("mode", "rule_search"),
                ("search_p_ruleset_deprecated", DropdownChoice.option_id(True)),
                ("search_p_ruleset_deprecated_USE", "on"),
            ])),
    )


@mode_registry.register
class ModeRulesetGroup(ABCRulesetMode):
    """Lists rulesets in a ruleset group"""
    @classmethod
    def name(cls):
        return "rulesets"

    @classmethod
    def permissions(cls):
        return ["rulesets"]

    def _from_vars(self):
        super()._from_vars()
        if not self._group_name:
            raise MKUserError(None, _("The mandatory group name is missing"))

    def _topic_breadcrumb_item(self) -> Optional[BreadcrumbItem]:
        """Return the BreadcrumbItem for the topic of this mode"""

        url = "wato.py?mode=rulesets&group=%s" % self._group_name
        main_module = main_module_registry.get(url)
        if main_module is None:
            # Anomaly: We should not reach this, but currently we do for some pages. Best we can do
            # at the moment is not to add a topic in this case.
            return None

        return BreadcrumbItem(
            title=main_module().topic.title,
            url=None,
        )

    def _get_page_type(self, search_options: Dict[str, str]) -> PageType:
        return PageType.RulesetGroup

    def _rulesets(self):
        return watolib.NonStaticChecksRulesets()

    def _set_title_and_help(self):
        rulegroup = watolib.get_rulegroup(self._group_name)
        self._title, self._help = rulegroup.title, rulegroup.help

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        self._extend_display_dropdown(menu)
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        if config.user.may("wato.hosts") or config.user.may("wato.seeall"):
            current_folder = Folder.current()
            yield PageMenuEntry(
                title=_("Hosts in folder: %s") % current_folder.title(),
                icon_name="folder",
                item=make_simple_link(current_folder.url()),
            )

            if html.request.get_ascii_input("host"):
                host_name = html.request.get_ascii_input_mandatory("host")
                yield PageMenuEntry(
                    title=_("Host properties of: %s") % host_name,
                    icon_name="host",
                    item=make_simple_link(
                        watolib.folder_preserving_link([("mode", "edit_host"),
                                                        ("host", host_name)])),
                )

        yield _page_menu_entry_predefined_conditions()

        if self._group_name == "agents":
            yield PageMenuEntry(
                title=_("Agent Bakery"),
                icon_name="agents",
                item=make_simple_link(watolib.folder_preserving_link([("mode", "agents")])),
            )

        yield PageMenuEntry(
            title=_("Rule search"),
            icon_name="search",
            item=make_simple_link(html.makeuri_contextless([
                ("mode", "rule_search"),
            ])),
        )

        yield from _page_menu_entries_predefined_searches()

    def _extend_display_dropdown(self, menu: PageMenu) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Filter"),
                entries=[
                    PageMenuEntry(
                        title="",
                        icon_name="trans",
                        item=PageMenuSearch(default_value=self._search_options.get("fulltext", "")),
                    )
                ],
            ))


@mode_registry.register
class ModeStaticChecksRulesets(ABCRulesetMode):
    @classmethod
    def name(cls):
        return "static_checks"

    @classmethod
    def permissions(cls):
        return ["rulesets"]

    def _get_page_type(self, search_options: Dict[str, str]) -> PageType:
        return PageType.RulesetGroup

    def _rulesets(self):
        return watolib.StaticChecksRulesets()

    def _set_title_and_help(self):
        rulegroup = watolib.get_rulegroup("static")
        self._title, self._help = rulegroup.title, rulegroup.help


def _page_menu_entry_predefined_conditions() -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Predefined conditions"),
        icon_name="condition",
        item=make_simple_link(watolib.folder_preserving_link([
            ("mode", "predefined_conditions"),
        ])),
    )


def _page_menu_entry_search_rules(search_options: SearchOptions, mode: str,
                                  page_type: PageType) -> PageMenuEntry:
    is_searching = bool(search_options)
    # Don't highlight the button on "standard page" searches. Meaning the page calls
    # that are no searches from the users point of view because he did not fill the
    # search form, but clicked a link in the GUI
    if is_searching:
        search_keys = sorted(search_options.keys())
        if (search_keys == ["ruleset_deprecated", "ruleset_group"] or
                _is_deprecated_rulesets_page(search_options) or
                _is_ineffective_rules_page(search_options) or
                _is_used_rulesets_page(search_options)):
            is_searching = False

    if is_searching:
        title = _("Refine search")
    else:
        title = _("Search")

    return PageMenuEntry(
        title=title,
        icon_name="search",
        item=make_simple_link(
            html.makeuri([
                ("mode", "rule_search_form"),
                ("back_mode", mode),
            ],
                         delvars=["filled_in"])),
        is_shortcut=page_type is PageType.RuleSearch and html.form_submitted(),
        is_suggested=page_type is PageType.RuleSearch and html.form_submitted(),
    )


def _is_deprecated_rulesets_page(search_options):
    return (list(search_options.keys()) == ["ruleset_deprecated"] and
            search_options["ruleset_deprecated"])


def _is_ineffective_rules_page(search_options):
    return search_options.get("ruleset_deprecated") is False \
           and search_options.get("rule_ineffective") is True


def _is_used_rulesets_page(search_options):
    return search_options.get("ruleset_deprecated") is False \
            and search_options.get("ruleset_used") is True


@mode_registry.register
class ModeEditRuleset(WatoMode):
    @classmethod
    def name(cls):
        return "edit_ruleset"

    @classmethod
    def permissions(cls):
        return []

    def __init__(self):
        super(ModeEditRuleset, self).__init__()
        store = PredefinedConditionStore()
        self._predefined_conditions = store.filter_usable_entries(store.load_for_reading())

    def _from_vars(self):
        self._folder = watolib.Folder.current()

        self._name = html.request.get_ascii_input_mandatory("varname")
        self._back_mode = html.request.get_ascii_input_mandatory(
            "back_mode", html.request.get_ascii_input_mandatory("ruleset_back_mode", "rulesets"))

        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

        self._item: Optional[ServiceName] = None
        self._service: Optional[ServiceName] = None
        self._hostname: Optional[HostName] = None

        # TODO: Clean this up. In which case is it used?
        # - The calculation for the service_description is not even correct, because it does not
        # take translations into account (see cmk.base.config.service_description()).
        check_command = html.request.get_ascii_input("check_command")
        if check_command:
            checks = watolib.check_mk_local_automation("get-check-information")
            if check_command.startswith("check_mk-"):
                check_command = check_command[9:]
                self._name = "checkgroup_parameters:" + checks[check_command].get("group", "")
                descr_pattern = checks[check_command]["service_description"].replace("%s", "(.*)")
                matcher = re.search(descr_pattern,
                                    html.request.get_unicode_input_mandatory("service_description"))
                if matcher:
                    try:
                        self._item = matcher.group(1)
                    except Exception:
                        pass
            elif check_command.startswith("check_mk_active-"):
                check_command = check_command[16:].split(" ")[0][:-1]
                self._name = "active_checks:" + check_command

        try:
            self._rulespec = rulespec_registry[self._name]
        except KeyError:
            raise MKUserError("varname", _("The ruleset \"%s\" does not exist.") % self._name)

        self._valuespec = self._rulespec.valuespec

        if not self._item:
            self._item = None
            if html.request.has_var("item"):
                try:
                    self._item = watolib.mk_eval(html.request.get_ascii_input_mandatory("item"))
                except Exception:
                    pass

        hostname = html.request.get_ascii_input("host")
        if hostname and self._folder.has_host(hostname):
            self._hostname = hostname

        # The service argument is only needed for performing match testing of rules
        if not self._service:
            self._service = None
            if html.request.has_var("service"):
                try:
                    self._service = watolib.mk_eval(
                        html.request.get_ascii_input_mandatory("service"))
                except Exception:
                    pass

        if self._hostname and self._rulespec.item_type == "item" and not self._service:
            raise MKUserError(
                "service",
                _("Unable to analyze matching, because \"service\" parameter is missing"))

        self._just_edited_rule_from_vars()

    # After actions like editing or moving a rule there is a rule that the user has been
    # working before. Focus this rule row again to make multiple actions with a single
    # rule easier to handle
    def _just_edited_rule_from_vars(self):
        if not html.request.has_var("rule_folder") or not html.request.has_var("rulenr"):
            self._just_edited_rule = None
            return

        rule_folder = watolib.Folder.folder(html.request.var("rule_folder"))
        rulesets = watolib.FolderRulesets(rule_folder)
        rulesets.load()
        ruleset = rulesets.get(self._name)

        self._just_edited_rule = None

        # rule number relative to folder
        rulenr = html.request.get_integer_input("rulenr")
        if rulenr is None:
            return

        try:
            self._just_edited_rule = ruleset.get_rule(rule_folder, rulenr)
        except KeyError:
            pass

    def _breadcrumb_url(self) -> str:
        return html.makeuri_contextless([("mode", self.name()), ("varname", self._name)],
                                        filename="wato.py")

    def title(self) -> str:
        assert self._rulespec.title is not None
        title = self._rulespec.title

        if self._hostname:
            title += _(" for host %s") % self._hostname
            if html.request.has_var("item") and self._rulespec.item_type:
                title += _(" and %s '%s'") % (self._rulespec.item_name, self._item)

        return title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield _page_menu_entry_predefined_conditions()

        if self._hostname:
            yield PageMenuEntry(
                title=_("Services"),
                icon_name="services",
                item=make_simple_link(
                    watolib.folder_preserving_link([("mode", "inventory"),
                                                    ("host", self._hostname)])),
            )

            if config.user.may('wato.rulesets'):
                yield PageMenuEntry(
                    title=_("Parameters"),
                    icon_name="rulesets",
                    item=make_simple_link(
                        watolib.folder_preserving_link([("mode", "object_parameters"),
                                                        ("host", self._hostname),
                                                        ("service", self._service or self._item)])),
                )

        if agent_bakery:
            yield from agent_bakery.page_menu_entries_agent_bakery(self._name)

        if self._name == "logwatch_rules":
            yield PageMenuEntry(
                title=_("Pattern analyzer"),
                icon_name="logwatch",
                item=make_simple_link(
                    watolib.folder_preserving_link([
                        ("mode", "pattern_editor"),
                        ("host", self._hostname),
                    ])),
                is_shortcut=True,
                is_suggested=True,
            )

    def action(self):
        rule_folder = watolib.Folder.folder(html.request.var("_folder", html.request.var("folder")))
        rule_folder.need_permission("write")
        rulesets = watolib.FolderRulesets(rule_folder)
        rulesets.load()
        ruleset = rulesets.get(self._name)

        try:
            # rule number relative to folder
            rulenr = html.request.get_integer_input_mandatory("_rulenr")
            rule = ruleset.get_rule(rule_folder, rulenr)
        except (IndexError, TypeError, ValueError, KeyError):
            raise MKUserError("rulenr",
                              _("You are trying to edit a rule which does not exist "
                                "anymore."))

        action = html.request.get_ascii_input_mandatory("_action")

        if action == "delete":
            c = wato_confirm(
                _("Confirm"),
                _("Delete rule number %d of folder '%s'?") % (rulenr + 1, rule_folder.alias_path()))
            if c:
                ruleset.delete_rule(rule)
                rulesets.save()
                return
            if c is False:  # not yet confirmed
                return ""
            return None  # browser reload

        if not html.check_transaction():
            return None  # browser reload

        if action == "up":
            ruleset.move_rule_up(rule)
        elif action == "down":
            ruleset.move_rule_down(rule)
        elif action == "top":
            ruleset.move_rule_to_top(rule)
        elif action == "move_to":
            ruleset.move_rule_to(rule, html.request.get_integer_input_mandatory("_index"))
        else:
            ruleset.move_rule_to_bottom(rule)
        rulesets.save()

    def page(self):
        if not config.wato_hide_varnames:
            display_varname = '%s["%s"]' % tuple(self._name.split(":")) \
                    if ':' in self._name else self._name
            html.div(display_varname, class_="varname")

        rulesets = watolib.SingleRulesetRecursively(self._name)
        rulesets.load()
        ruleset = rulesets.get(self._name)

        html.help(ruleset.help())
        self._explain_match_type(ruleset.match_type())
        self._rule_listing(ruleset)
        self._create_form()

    def _explain_match_type(self, match_type):
        html.b("%s: " % _("Matching"))
        if match_type == "first":
            html.write_text(_("The first matching rule defines the parameter."))

        elif match_type == "dict":
            html.write_text(
                _("Each parameter is defined by the first matching rule where that "
                  "parameter is set (checked)."))

        elif match_type in ("all", "list"):
            html.write_text(_("All matching rules will add to the resulting list."))

        else:
            html.write_text(_("Unknown match type: %s") % match_type)

    def _rule_listing(self, ruleset):
        rules = ruleset.get_rules()
        if not rules:
            html.div(_("There are no rules defined in this set."), class_="info")
            return
        match_state = {"matched": False, "keys": set()}
        search_options = ModeRuleSearchForm().search_options
        groups = (
            (folder, folder_rules)  #
            for folder, folder_rules in itertools.groupby(rules, key=lambda rule: rule[0])
            if folder.is_transitive_parent_of(self._folder) or
            self._folder.is_transitive_parent_of(folder))

        num_rows = 0
        for folder, folder_rules in groups:
            with table_element("rules_%s_%s" % (self._name, folder.ident()),
                               title="%s %s (%d)" %
                               (_("Rules in folder"), folder.alias_path(show_main=False),
                                ruleset.num_rules_in_folder(folder)),
                               css="ruleset",
                               searchable=False,
                               sortable=False,
                               limit=None,
                               foldable=True) as table:
                for _folder, rulenr, rule in folder_rules:
                    num_rows += 1
                    table.row(css=self._css_for_rule(search_options, rule))
                    self._set_focus(rulenr, rule)
                    self._show_rule_icons(table, match_state, folder, rulenr, rule)
                    self._rule_cells(table, rule)

        headinfo = _("1 row") if num_rows == 1 else _("%d rows") % num_rows
        html.javascript("cmk.utils.update_header_info(%s);" % json.dumps(headinfo))

    @staticmethod
    def _css_for_rule(search_options, rule):
        css = []
        if rule.is_disabled():
            css.append("disabled")
        if (rule.ruleset.has_rule_search_options(search_options) and
                rule.matches_search(search_options) and
            ("fulltext" not in search_options or
             not rule.ruleset.matches_fulltext_search(search_options))):
            css.append("matches_search")
        return " ".join(css) if css else None

    def _set_focus(self, rulenr, rule):
        if self._just_edited_rule and self._just_edited_rule.folder == rule.folder and self._just_edited_rule.index(
        ) == rulenr:
            html.focus_here()

    def _show_rule_icons(self, table, match_state, folder, rulenr, rule):
        if self._hostname:
            table.cell(_("Ma."))
            title, img = self._match(match_state, rule)
            html.icon("rule%s" % img, title, middle=True)

        table.cell("", css="buttons")
        if rule.is_disabled():
            html.icon("disabled", _("This rule is currently disabled and will not be applied"))
        else:
            html.empty_icon()

        table.cell(_("Actions"), css="buttons rulebuttons")
        edit_url = watolib.folder_preserving_link([
            ("mode", "edit_rule"),
            ("ruleset_back_mode", self._back_mode),
            ("varname", self._name),
            ("rulenr", rulenr),
            ("host", self._hostname),
            ("item", ensure_str(watolib.mk_repr(self._item))),
            ("service", ensure_str(watolib.mk_repr(self._service))),
            ("rule_folder", folder.path()),
        ])
        html.icon_button(edit_url, _("Edit this rule"), "edit")

        clone_url = watolib.folder_preserving_link([
            ("mode", "clone_rule"),
            ("ruleset_back_mode", self._back_mode),
            ("varname", self._name),
            ("rulenr", rulenr),
            ("host", self._hostname),
            ("item", ensure_str(watolib.mk_repr(self._item))),
            ("service", ensure_str(watolib.mk_repr(self._service))),
            ("rule_folder", folder.path()),
        ])
        html.icon_button(clone_url, _("Create a copy of this rule"), "clone")

        html.element_dragger_url("tr", base_url=self._action_url("move_to", folder, rulenr))
        self._rule_button("delete", _("Delete this rule"), folder, rulenr)

    def _match(self, match_state, rule):
        reasons = [_("This rule is disabled")] if rule.is_disabled() else list(
            rule.get_mismatch_reasons(
                self._folder, self._hostname, self._item, self._service,
                only_host_conditions=False))
        if reasons:
            return _("This rule does not match: %s") % " ".join(reasons), 'nmatch'
        ruleset = rule.ruleset
        if ruleset.match_type() == "dict":
            new_keys = set(rule.value.keys())
            already_existing = match_state["keys"] & new_keys
            match_state["keys"] |= new_keys
            if not new_keys:
                return _("This rule matches, but does not define any parameters."), 'imatch'
            if not already_existing:
                return _("This rule matches and defines new parameters."), 'match'
            if already_existing == new_keys:
                return _(
                    "This rule matches, but all of its parameters are overridden by previous rules."
                ), 'imatch'
            return _(
                "This rule matches, but some of its parameters are overridden by previous rules."
            ), 'pmatch'
        if match_state["matched"] and ruleset.match_type() != "all":
            return _("This rule matches, but is overridden by a previous rule."), 'imatch'
        match_state["matched"] = True
        return (_("This rule matches for the host '%s'") % self._hostname) + \
            (_(" and the %s '%s'.") % (ruleset.item_name(), self._item) if ruleset.item_type() else "."), \
            'match'

    def _action_url(self, action, folder, rulenr):
        vars_ = [
            ("mode", html.request.var('mode', 'edit_ruleset')),
            ("ruleset_back_mode", self._back_mode),
            ("varname", self._name),
            ("_folder", folder.path()),
            ("_rulenr", str(rulenr)),
            ("_action", action),
        ]
        if html.request.var("rule_folder"):
            vars_.append(("rule_folder", folder.path()))
        if html.request.var("host"):
            vars_.append(("host", self._hostname))
        if html.request.var("item"):
            vars_.append(("item", watolib.mk_repr(self._item)))
        if html.request.var("service"):
            vars_.append(("service", watolib.mk_repr(self._service)))

        return make_action_link(vars_)

    def _rule_button(self, action, title=None, folder=None, rulenr=0):
        html.icon_button(self._action_url(action, folder, rulenr), title, action)

    # TODO: Refactor this whole method
    def _rule_cells(self, table, rule):
        value = rule.value
        rule_options = rule.rule_options

        # Conditions
        table.cell(_("Conditions"), css="condition")
        self._rule_conditions(rule)

        # Value
        table.cell(_("Value"))
        try:
            value_html = HTML(self._valuespec.value_to_text(value))
        except Exception as e:
            try:
                reason = "%s" % e
                self._valuespec.validate_datatype(value, "")
            except Exception as e:
                reason = "%s" % e

            value_html = html.render_icon("alert") \
                       + _("The value of this rule is not valid. ") \
                       + reason
        html.write_html(value_html)

        # Comment
        table.cell(_("Description"))
        url = rule_options.get("docu_url")
        if url:
            html.icon_button(url, _("Context information about this rule"), "url", target="_blank")
            html.write("&nbsp;")

        desc = rule_options.get("description") or rule_options.get("comment", "")
        html.write_text(desc)

    def _rule_conditions(self, rule):
        self._predefined_condition_info(rule)
        html.write(
            VSExplicitConditions(rulespec=self._rulespec).value_to_text(rule.get_rule_conditions()))

    def _predefined_condition_info(self, rule):
        condition_id = rule.predefined_condition_id()
        if condition_id is None:
            return

        condition = self._predefined_conditions[condition_id]
        url = watolib.folder_preserving_link([
            ("mode", "edit_predefined_condition"),
            ("ident", condition_id),
        ])
        html.write(_("Predefined condition: <a href=\"%s\">%s</a>") % (url, condition["title"]))

    def _create_form(self):
        html.begin_form("new_rule", add_transid=False)
        html.hidden_field("ruleset_back_mode", self._back_mode, add_var=True)

        html.open_table()
        if self._hostname:
            label = _("Host %s") % self._hostname
            ty = _('Host')
            if self._item is not None and self._rulespec.item_type:
                assert self._rulespec.item_name is not None
                label += _(" and %s '%s'") % (self._rulespec.item_name, self._item)
                ty = self._rulespec.item_name

            html.open_tr()
            html.open_td()
            html.button("_new_host_rule", _("Create %s specific rule for: ") % ty)
            html.hidden_field("host", self._hostname)
            html.hidden_field("item", ensure_str(watolib.mk_repr(self._item)))
            html.hidden_field("service", ensure_str(watolib.mk_repr(self._service)))
            html.close_td()
            html.open_td(style="vertical-align:middle")
            html.write_text(label)
            html.close_td()
            html.close_tr()

        html.open_tr()
        html.open_td()
        html.button("_new_rule", _("Create rule in folder: "))
        html.close_td()
        html.open_td()

        html.dropdown("rule_folder", watolib.Folder.folder_choices(), deflt=self._folder.path())
        html.close_td()
        html.close_tr()
        html.close_table()
        html.write_text("\n")
        html.hidden_field("varname", self._name)
        html.hidden_field("mode", "new_rule")
        html.hidden_field('folder', self._folder.path())
        html.end_form()


@mode_registry.register
class ModeRuleSearchForm(WatoMode):
    @classmethod
    def name(cls):
        return "rule_search_form"

    @classmethod
    def permissions(cls):
        return ["rulesets"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeRuleSearch

    def __init__(self):
        self.back_mode = html.request.get_ascii_input_mandatory("back_mode", "rulesets")
        super().__init__()

    def title(self):
        if self.search_options:
            return _("Refine search")
        return _("Search rulesets and rules")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb,
                                          form_name="rule_search",
                                          button_name="_do_search",
                                          save_title=_("Search"))
        action_topic = menu.dropdowns[0].topics[0]
        action_topic.entries.insert(
            1,
            PageMenuEntry(
                title=_("Reset"),
                icon_name="reset",
                item=make_form_submit_link("rule_search", "_reset_search"),
                is_shortcut=True,
                is_suggested=True,
            ))
        return menu

    def page(self):
        html.begin_form("rule_search", method="GET")
        html.hidden_field("mode", self.back_mode, add_var=True)

        valuespec = self._valuespec()
        valuespec.render_input_as_form("search", self.search_options)

        html.hidden_fields()
        html.end_form()

    def _from_vars(self):
        if html.request.var("_reset_search"):
            html.request.del_vars("search_")
            self.search_options: SearchOptions = {}
            return

        value = self._valuespec().from_html_vars("search")
        self._valuespec().validate_value(value, "search")

        # In case all checkboxes are unchecked, treat this like the reset search button press
        # and remove all vars
        if not value:
            html.request.del_vars("search_")

        self.search_options = value

    def _valuespec(self):
        return Dictionary(
            title=_("Search rulesets"),
            headers=[
                (_("Fulltext search"), [
                    "fulltext",
                ]),
                (_("Rulesets"), [
                    "ruleset_group",
                    "ruleset_name",
                    "ruleset_title",
                    "ruleset_help",
                    "ruleset_deprecated",
                    "ruleset_used",
                ]),
                (_("Rules"), [
                    "rule_description",
                    "rule_comment",
                    "rule_value",
                    "rule_host_list",
                    "rule_item_list",
                    "rule_hosttags",
                    "rule_disabled",
                    "rule_ineffective",
                    "rule_folder",
                    "rule_predefined_condition",
                ]),
            ],
            elements=[
                ("fulltext",
                 RegExpUnicode(
                     title=_("Rules matching pattern"),
                     help=_("Use this field to search the description, comment, host and "
                            "service conditions including the text representation of the "
                            "configured values."),
                     size=60,
                     mode=RegExpUnicode.infix,
                 )),
                ("ruleset_group", _vs_ruleset_group(self.back_mode)),
                ("ruleset_name", RegExpUnicode(
                    title=_("Name"),
                    size=60,
                    mode=RegExpUnicode.infix,
                )),
                ("ruleset_title", RegExpUnicode(
                    title=_("Title"),
                    size=60,
                    mode=RegExpUnicode.infix,
                )),
                ("ruleset_help", RegExpUnicode(
                    title=_("Help"),
                    size=60,
                    mode=RegExpUnicode.infix,
                )),
                ("ruleset_deprecated",
                 DropdownChoice(
                     title=_("Deprecated"),
                     choices=[
                         (True, _("Search for deprecated rulesets")),
                         (False, _("Search for not deprecated rulesets")),
                     ],
                 )),
                ("ruleset_used",
                 DropdownChoice(
                     title=_("Used"),
                     choices=[
                         (True, _("Search for rulesets that have rules configured")),
                         (False, _("Search for rulesets that don't have rules configured")),
                     ],
                 )),
                ("rule_description",
                 RegExpUnicode(
                     title=_("Description"),
                     size=60,
                     mode=RegExpUnicode.infix,
                 )),
                ("rule_comment",
                 RegExpUnicode(
                     title=_("Comment"),
                     size=60,
                     mode=RegExpUnicode.infix,
                 )),
                ("rule_value", RegExpUnicode(
                    title=_("Value"),
                    size=60,
                    mode=RegExpUnicode.infix,
                )),
                ("rule_host_list",
                 RegExpUnicode(
                     title=_("Host match list"),
                     size=60,
                     mode=RegExpUnicode.infix,
                 )),
                ("rule_item_list",
                 RegExpUnicode(
                     title=_("Item match list"),
                     size=60,
                     mode=RegExpUnicode.infix,
                 )),
                ("rule_hosttags", HostTagCondition(title=_("Used host tags"))),
                ("rule_disabled",
                 DropdownChoice(
                     title=_("Disabled"),
                     choices=[
                         (True, _("Search for disabled rules")),
                         (False, _("Search for enabled rules")),
                     ],
                 )),
                ("rule_ineffective",
                 DropdownChoice(
                     title=_("Ineffective"),
                     choices=[
                         (True,
                          _("Search for ineffective rules (not matching any host or service)")),
                         (False, _("Search for effective rules")),
                     ],
                 )),
                ("rule_folder",
                 Tuple(
                     title=_("Folder"),
                     orientation="horizontal",
                     elements=[
                         DropdownChoice(
                             title=_("Selection"),
                             choices=watolib.Folder.folder_choices(),
                         ),
                         DropdownChoice(
                             title=_("Recursion"),
                             choices=[
                                 (True, _("Also search in subfolders")),
                                 (False, _("Search in this folder")),
                             ],
                             default_value=False,
                         ),
                     ],
                 )),
                ("rule_predefined_condition",
                 DropdownChoice(
                     title=_("Using predefined condition"),
                     choices=PredefinedConditionStore().choices(),
                     sorted=True,
                 )),
            ],
        )


def _vs_ruleset_group(mode_name: str) -> DropdownChoice:
    return DropdownChoice(
        title=_("Group"),
        choices=lambda: rulespec_group_registry.get_group_choices(mode_name),
    )


class EditRuleMode(WatoMode):
    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditRuleset

    def _from_vars(self):
        self._name = html.request.get_ascii_input_mandatory("varname")

        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

        try:
            self._rulespec = rulespec_registry[self._name]
        except KeyError:
            raise MKUserError("varname", _("The ruleset \"%s\" does not exist.") % self._name)

        self._back_mode = html.request.get_ascii_input_mandatory('back_mode', 'edit_ruleset')

        self._set_folder()

        self._rulesets = watolib.FolderRulesets(self._folder)
        self._rulesets.load()
        self._ruleset = self._rulesets.get(self._name)

        self._set_rule()

    def _set_folder(self):
        self._folder = watolib.Folder.folder(html.request.get_ascii_input_mandatory("rule_folder"))

    def _set_rule(self):
        if html.request.has_var("rulenr"):
            try:
                rulenr = html.request.get_integer_input_mandatory("rulenr")
                self._rule = self._ruleset.get_rule(self._folder, rulenr)
            except (KeyError, TypeError, ValueError, IndexError):
                raise MKUserError(
                    "rulenr", _("You are trying to edit a rule which does "
                                "not exist anymore."))
        elif html.request.has_var("_export_rule"):
            self._rule = watolib.Rule(self._folder, self._ruleset)
            self._update_rule_from_vars()

        else:
            raise NotImplementedError()

    def title(self):
        return _("Edit rule: %s") % self._rulespec.title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        # TODO: Is this still needed + for which case?
        if self._back_mode == 'edit_ruleset':
            var_list: HTTPVariables = [
                ("mode", "edit_ruleset"),
                ("varname", self._name),
                ("host", html.request.get_ascii_input_mandatory("host", "")),
            ]
            if html.request.has_var("item"):
                var_list.append(("item", html.request.get_unicode_input_mandatory("item")))
            if html.request.has_var("service"):
                var_list.append(("service", html.request.get_unicode_input_mandatory("service")))
            backurl = watolib.folder_preserving_link(var_list)

        else:
            backurl = watolib.folder_preserving_link([
                ('mode', self._back_mode),
                ("host", html.request.get_ascii_input_mandatory("host", ""))
            ])

        menu = make_simple_form_page_menu(breadcrumb,
                                          form_name="rule_editor",
                                          button_name="save",
                                          abort_url=backurl)

        action_dropdown = menu.dropdowns[0]
        action_dropdown.topics.append(
            PageMenuTopic(
                title=_("For Web API"),
                entries=[
                    PageMenuEntry(
                        title=_("Export for API"),
                        icon_name="export",
                        item=make_form_submit_link("rule_editor", "_export_rule"),
                    ),
                ],
            ))

        menu.dropdowns.insert(
            1,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=list(self._page_menu_entries_related()),
                    ),
                ],
            ))

        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield _page_menu_entry_predefined_conditions()

    def breadcrumb(self) -> Breadcrumb:
        # Let the ModeRulesetGroup know the group we are currently editing
        with html.stashed_vars():
            html.request.set_var("group", self._ruleset.rulespec.main_group_name)
            return super().breadcrumb()

    def action(self):
        if not html.check_transaction():
            return self._back_mode

        self._update_rule_from_vars()

        # Check permissions on folders
        new_rule_folder = watolib.Folder.folder(self._get_rule_conditions_from_vars().host_folder)
        if not isinstance(self, ModeNewRule):
            self._folder.need_permission("write")
        new_rule_folder.need_permission("write")

        if html.request.has_var("_export_rule"):
            return "edit_rule"

        if new_rule_folder == self._folder:
            self._rule.folder = new_rule_folder
            self._save_rule()

        else:
            # Move rule to new folder during editing
            self._remove_from_orig_folder()

            # Set new folder
            self._rule.folder = new_rule_folder

            self._rulesets = watolib.FolderRulesets(new_rule_folder)
            self._rulesets.load()
            self._ruleset = self._rulesets.get(self._name)
            self._ruleset.append_rule(new_rule_folder, self._rule)
            self._rulesets.save()

            affected_sites = list(set(self._folder.all_site_ids() + new_rule_folder.all_site_ids()))
            add_change(
                "edit-rule",
                _("Changed properties of rule \"%s\", moved rule from "
                  "folder \"%s\" to \"%s\"") %
                (self._ruleset.title(), self._folder.alias_path(), new_rule_folder.alias_path()),
                sites=affected_sites)

        return (self._back_mode, self._success_message())

    def _update_rule_from_vars(self):
        # Additional options
        rule_options = self._vs_rule_options().from_html_vars("options")
        self._vs_rule_options().validate_value(rule_options, "options")
        self._rule.rule_options = rule_options

        if self._get_condition_type_from_vars() == "predefined":
            condition_id = self._get_condition_id_from_vars()
            self._rule.rule_options["predefined_condition_id"] = condition_id

        # CONDITION
        self._rule.update_conditions(self._get_rule_conditions_from_vars())

        # VALUE
        value = self._ruleset.valuespec().from_html_vars("ve")
        self._ruleset.valuespec().validate_value(value, "ve")
        self._rule.value = value

    def _get_condition_type_from_vars(self):
        condition_type = self._vs_condition_type().from_html_vars("condition_type")
        self._vs_condition_type().validate_value(condition_type, "condition_type")
        return condition_type

    def _get_condition_id_from_vars(self):
        condition_id = self._vs_predefined_condition_id().from_html_vars("predefined_condition_id")
        self._vs_predefined_condition_id().validate_value(condition_id, "predefined_condition_id")
        return condition_id

    def _get_rule_conditions_from_vars(self) -> RuleConditions:
        if self._get_condition_type_from_vars() == "predefined":
            return self._get_predefined_rule_conditions(self._get_condition_id_from_vars())
        return self._get_explicit_rule_conditions()

    def _get_predefined_rule_conditions(self, condition_id):
        store = PredefinedConditionStore()
        store_entries = store.filter_usable_entries(store.load_for_reading())
        return RuleConditions(**store_entries[condition_id]["conditions"])

    @abc.abstractmethod
    def _save_rule(self):
        raise NotImplementedError()

    def _remove_from_orig_folder(self):
        self._ruleset.delete_rule(self._rule)
        self._rulesets.save()

    def _success_message(self):
        return _("Edited rule in ruleset \"%s\" in folder \"%s\"") % \
                 (self._ruleset.title(), self._folder.alias_path())

    def _get_explicit_rule_conditions(self):
        vs = self._vs_explicit_conditions()
        conditions = vs.from_html_vars("explicit_conditions")
        vs.validate_value(conditions, "explicit_conditions")
        return conditions

    def page(self):
        if html.request.has_var("_export_rule"):
            self._show_rule_representation()

        else:
            self._show_rule_editor()

    def _show_rule_editor(self):
        if self._ruleset.help():
            html.div(HTML(self._ruleset.help()), class_="info")

        html.begin_form("rule_editor", method="POST")

        # Additonal rule options
        self._vs_rule_options().render_input("options", self._rule.rule_options)

        # Value
        valuespec = self._ruleset.valuespec()
        forms.header(valuespec.title() or _("Value"))
        forms.section()
        html.prevent_password_auto_completion()
        try:
            valuespec.validate_datatype(self._rule.value, "ve")
            valuespec.render_input("ve", self._rule.value)
        except Exception as e:
            if config.debug:
                raise
            html.show_warning(
                _('Unable to read current options of this rule. Falling back to '
                  'default values. When saving this rule now, your previous settings '
                  'will be overwritten. Problem was: %s.') % e)

            # In case of validation problems render the input with default values
            valuespec.render_input("ve", valuespec.default_value())

        valuespec.set_focus("ve")

        self._show_conditions()

        forms.end()

        html.hidden_fields()
        self._vs_rule_options().set_focus("options")
        html.end_form()

    def _show_conditions(self):
        forms.header(_("Conditions"))

        condition_type = "predefined" if self._rule.predefined_condition_id() else "explicit"

        forms.section(_("Condition type"))
        self._vs_condition_type().render_input(varprefix="condition_type", value=condition_type)
        self._show_predefined_conditions()
        self._show_explicit_conditions()
        html.javascript("cmk.wato.toggle_rule_condition_type(\"condition_type\")")

    def _vs_condition_type(self):
        return DropdownChoice(
            title=_("Condition type"),
            help=_("You can either specify individual conditions for this rule, or use a set of "
                   "predefined conditions, which may be handy if you have to configure the "
                   "same conditions in different rulesets."),
            choices=[
                ("explicit", _("Explicit conditions")),
                ("predefined", _("Predefined conditions")),
            ],
            on_change="cmk.wato.toggle_rule_condition_type(\"condition_type\")",
            encode_value=False,
        )

    def _show_predefined_conditions(self):
        forms.section(_("Predefined condition"), css="condition predefined")
        self._vs_predefined_condition_id().render_input(
            varprefix="predefined_condition_id",
            value=self._rule.predefined_condition_id(),
        )

    def _vs_predefined_condition_id(self):
        url = watolib.folder_preserving_link([("mode", "predefined_conditions")])
        return DropdownChoice(
            title=_("Predefined condition"),
            choices=PredefinedConditionStore().choices(),
            sorted=True,
            invalid_choice="complain",
            invalid_choice_title=_(
                "Predefined condition '%s' does not exist or using not permitted"),
            invalid_choice_error=_(
                "The configured predefined condition has either be removed or you "
                "are not permitted to use it. Please choose another one."),
            empty_text=(_("There are no elements defined for this selection yet.") + " " +
                        _("You can create predefined conditions <a href=\"%s\">here</a>.") % url))

    def _show_explicit_conditions(self):
        vs = self._vs_explicit_conditions(render="form_part")
        value = self._rule.get_rule_conditions()

        try:
            vs.validate_datatype(value, "explicit_conditions")
            vs.render_input("explicit_conditions", value)
        except Exception as e:
            forms.section("", css="condition explicit")
            html.show_warning(
                _('Unable to read current conditions of this rule. Falling back to '
                  'default values. When saving this rule now, your previous settings '
                  'will be overwritten. Problem was: %s, Previous conditions: <pre>%s</pre>'
                  'Such an issue may be caused by an inconsistent configuration, e.g. when '
                  'rules refer to tag groups or tags that do not exist anymore.') %
                (e, value.to_config_with_folder()))

            # In case of validation problems render the input with default values
            vs.render_input("explicit_conditions", RuleConditions(host_folder=self._folder.path()))

    def _vs_explicit_conditions(self, **kwargs):
        return VSExplicitConditions(rulespec=self._rulespec, **kwargs)

    def _show_rule_representation(self):
        content = "<pre>%s</pre>" % html.render_text(pprint.pformat(self._rule.to_config()))

        html.write(_("This rule representation can be used for Web API calls."))
        html.br()
        html.br()

        html.open_center()
        html.open_table(class_="progress")

        html.open_tr()
        html.th("Rule representation for Web API")
        html.close_tr()

        html.open_tr()
        html.td(html.render_div(content, id_="rule_representation"), class_="log")
        html.close_tr()

        html.close_table()
        html.close_center()

    def _vs_rule_options(self, disabling=True):
        return Dictionary(
            title=_("Rule Properties"),
            optional_keys=False,
            render="form",
            elements=rule_option_elements(disabling),
        )


class VSExplicitConditions(Transform):
    """Valuespec for editing a set of explicit rule conditions"""
    def __init__(self, rulespec, **kwargs):
        self._rulespec = rulespec
        super(VSExplicitConditions, self).__init__(
            Dictionary(elements=self._condition_elements(),
                       headers=[
                           (_("Folder"), "condition explicit", ["folder_path"]),
                           (_("Host tags"), "condition explicit", ["host_tags"]),
                           (_("Host labels"), "condition explicit", ["host_labels"]),
                           (_("Explicit hosts"), "condition explicit", ["explicit_hosts"]),
                           (self._service_title(), "condition explicit", ["explicit_services"]),
                           (_("Service labels"), "condition explicit", ["service_labels"]),
                       ],
                       optional_keys=["explicit_hosts", "explicit_services"],
                       **kwargs),
            forth=self._to_valuespec,
            back=self._from_valuespec,
        )

    def _condition_elements(self):
        elements = [
            ("folder_path", self._vs_folder()),
            ("host_tags", self._vs_host_tag_condition()),
        ]

        if self._allow_label_conditions():
            elements.append(("host_labels", self._vs_host_label_condition()))

        elements.append(("explicit_hosts", self._vs_explicit_hosts()))
        elements += self._service_elements()

        return elements

    def _to_valuespec(self, conditions: RuleConditions) -> Dict:
        explicit: Dict = {
            "folder_path": conditions.host_folder,
            "host_tags": conditions.host_tags,
        }

        if self._allow_label_conditions():
            explicit["host_labels"] = conditions.host_labels

        explicit_hosts = conditions.host_list
        if explicit_hosts is not None:
            explicit["explicit_hosts"] = explicit_hosts

        if self._rulespec.item_type:
            explicit_services = conditions.item_list
            if explicit_services is not None:
                explicit["explicit_services"] = explicit_services

            if self._allow_label_conditions():
                explicit["service_labels"] = conditions.service_labels

        return explicit

    def _allow_label_conditions(self):
        """Rulesets that influence the labels of hosts or services must not use label conditions"""
        return self._rulespec.name not in [
            "host_label_rules",
            "service_label_rules",
        ]

    def _service_elements(self):
        if not self._rulespec.item_type:
            return []

        elements = [("explicit_services", self._vs_explicit_services())]

        if self._allow_label_conditions():
            elements.append(("service_labels", self._vs_service_label_condition()))

        return elements

    def _service_title(self):
        item_type = self._rulespec.item_type
        if not item_type:
            return None

        if item_type == "service":
            return _("Services")

        if item_type == "checktype":
            return _("Check types")

        if item_type == "item":
            return self._rulespec.item_name.title()

        raise MKUserError(None, "Invalid item type '%s'" % item_type)

    def _from_valuespec(self, explicit: dict) -> RuleConditions:

        service_description = None
        service_labels = None
        if self._rulespec.item_type:
            service_description = self._condition_list_from_valuespec(
                explicit.get("explicit_services"), is_service=True)
            service_labels = explicit["service_labels"] if self._allow_label_conditions() else {}

        return RuleConditions(
            host_folder=explicit["folder_path"],
            host_tags=explicit["host_tags"],
            host_labels=explicit["host_labels"] if self._allow_label_conditions() else {},
            host_name=self._condition_list_from_valuespec(explicit.get("explicit_hosts"),
                                                          is_service=False),
            service_description=service_description,
            service_labels=service_labels,
        )

    def _condition_list_from_valuespec(self, conditions, is_service):
        if conditions is None:
            return None

        condition_list, negate = conditions

        sub_conditions = []
        for entry in condition_list:
            if is_service:
                sub_conditions.append({"$regex": entry})
                continue

            if entry[0] == '~':
                sub_conditions.append({"$regex": entry[1:]})
                continue
            sub_conditions.append(entry)

        if not sub_conditions:
            raise MKUserError(
                None, _("Please specify at least one condition or this rule will never match."))

        if negate:
            return {"$nor": sub_conditions}
        return sub_conditions

    def _vs_folder(self):
        return DropdownChoice(
            title=_("Folder"),
            help=_("The rule is only applied to hosts directly in or below this folder."),
            choices=watolib.Folder.folder_choices(),
            encode_value=False,
        )

    def _vs_host_label_condition(self):
        return LabelCondition(
            title=_("Host labels"),
            help_txt=_("Use this condition to select hosts based on the configured host labels."),
        )

    def _vs_service_label_condition(self):
        return LabelCondition(
            title=_("Service labels"),
            help_txt=_(
                "Use this condition to select services based on the configured service labels."),
        )

    def _vs_host_tag_condition(self):
        return DictHostTagCondition(
            title=_("Host tags"),
            help_txt=_("The rule will only be applied to hosts fulfilling all "
                       "of the host tag conditions listed here, even if they appear "
                       "in the list of explicit host names."),
        )

    def _vs_explicit_hosts(self):
        return Tuple(
            title=_("Explicit hosts"),
            elements=[
                ListOfStrings(
                    orientation="horizontal",
                    valuespec=ConfigHostname(size=30, validate=self._validate_list_entry),
                    help=
                    _("Here you can enter a list of explicit host names that the rule should or should "
                      "not apply to. Leave this option disabled if you want the rule to "
                      "apply for all hosts specified by the given tags. The names that you "
                      "enter here are compared with case sensitive exact matching. Alternatively "
                      "you can use regular expressions if you enter a tilde (<tt>~</tt>) as the first "
                      "character. That regular expression must match the <i>beginning</i> of "
                      "the host names in question."),
                ),
                Checkbox(
                    label=_("<b>Negate:</b> make rule apply for <b>all but</b> the above hosts"),),
            ],
        )

    def _vs_explicit_services(self):
        return Tuple(
            title=self._service_title(),
            elements=[
                self._vs_service_conditions(),
                Checkbox(label=_(
                    "<b>Negate:</b> make rule apply for <b>all but</b> the above entries"),),
            ],
        )

    def _explicit_service_help_text(self):
        itemtype = self._rulespec.item_type
        if itemtype == "service":
            return _("Specify a list of service patterns this rule shall apply to. "
                     "The patterns must match the <b>beginning</b> of the service "
                     "in question. Adding a <tt>$</tt> to the end forces an excact "
                     "match. Pattern use <b>regular expressions</b>. A <tt>.*</tt> will "
                     "match an arbitrary text.")

        if itemtype == "item":
            if self._rulespec.item_help:
                return self._rulespec.item_help

            return _("You can make the rule apply only to certain services of the "
                     "specified hosts. Do this by specifying explicit <b>items</b> to "
                     "match here. <b>Hint:</b> make sure to enter the item only, "
                     "not the full Service description. "
                     "<b>Note:</b> the match is done on the <u>beginning</u> "
                     "of the item in question. Regular expressions are interpreted, "
                     "so appending a <tt>$</tt> will force an exact match.")

        return None

    def _vs_service_conditions(self):
        itemenum = self._rulespec.item_enum
        if itemenum:
            return Transform(
                ListChoice(
                    choices=itemenum,
                    columns=3,
                ),
                forth=lambda item_list: [x + "$" for x in item_list],
                back=lambda item_list: [x.rstrip("$") for x in item_list],
            )

        return ListOfStrings(
            orientation="horizontal",
            valuespec=RegExpUnicode(size=30,
                                    mode=RegExpUnicode.prefix,
                                    validate=self._validate_list_entry),
            help=self._explicit_service_help_text(),
        )

    def _validate_list_entry(self, value, varprefix):
        if value.startswith("!"):
            raise MKUserError(varprefix, _("It's not allowed to use a leading \"!\" here."))

    def value_to_text(self, value: RuleConditions) -> str:
        with html.plugged():
            html.open_ul(class_="conditions")
            renderer = RuleConditionRenderer()
            for condition in renderer.render(self._rulespec, value):
                html.li(condition, class_="condition")
            html.close_ul()
            return html.drain()


class RuleConditionRenderer:
    def render(self, rulespec: Rulespec, conditions: RuleConditions) -> List[str]:
        rendered: List[str] = []
        rendered += list(self._tag_conditions(conditions))
        rendered += list(self._host_label_conditions(conditions))
        rendered += list(self._host_conditions(conditions))
        rendered += list(self._service_conditions(rulespec, conditions))
        rendered += list(self._service_label_conditions(conditions))
        return rendered

    def _tag_conditions(self, conditions: RuleConditions) -> Generator:
        for tag_spec in conditions.host_tags.values():
            if isinstance(tag_spec, dict) and "$or" in tag_spec:
                yield HTML(" <i>or</i> ").join(
                    [self._single_tag_condition(sub_spec) for sub_spec in tag_spec["$or"]])
            elif isinstance(tag_spec, dict) and "$nor" in tag_spec:
                yield HTML(_("Neither") + " ") + HTML(" <i>nor</i> ").join(
                    [self._single_tag_condition(sub_spec) for sub_spec in tag_spec["$nor"]])
            else:
                yield self._single_tag_condition(tag_spec)

    def _single_tag_condition(self, tag_spec):
        negate = False
        if isinstance(tag_spec, dict):
            if "$ne" in tag_spec:
                negate = True
            else:
                raise NotImplementedError()

        if negate:
            tag_id = tag_spec["$ne"]
        else:
            tag_id = tag_spec

        tag = config.tags.get_tag_or_aux_tag(tag_id)
        if tag and tag.title:
            if not tag.is_aux_tag:
                if negate:
                    return HTML(
                        _("Host: %s is <b>not</b> <b>%s</b>") % (tag.group.title, tag.title))
                return HTML(_("Host: %s is <b>%s</b>") % (tag.group.title, tag.title))

            if negate:
                return HTML(_("Host does not have tag <b>%s</b>") % tag.title)
            return HTML(_("Host has tag <b>%s</b>") % tag.title)

        if negate:
            return HTML(_("Unknown tag: Host has <b>not</b> the tag <tt>%s</tt>") % tag_id)

        return HTML(_("Unknown tag: Host has the tag <tt>%s</tt>") % tag_id)

    def _host_label_conditions(self, conditions: RuleConditions) -> Generator:
        return self._label_conditions(conditions.host_labels, "host", _("Host"))

    def _service_label_conditions(self, conditions: RuleConditions) -> Generator:
        return self._label_conditions(conditions.service_labels, "service", _("Service"))

    def _label_conditions(self, label_conditions, object_type, object_title):
        if not label_conditions:
            return

        labels_html = (self._single_label_condition(object_type, label_id, label_spec)
                       for label_id, label_spec in label_conditions.items())
        yield HTML(
            _("%s matching labels: %s") %
            (object_title, html.render_i(_("and"), class_="label_operator").join(labels_html)))

    def _single_label_condition(self, object_type, label_id, label_spec):
        negate = False
        label_value = label_spec
        if isinstance(label_spec, dict):
            if "$ne" in label_spec:
                negate = True
                label_value = label_spec["$ne"]
            else:
                raise NotImplementedError()

        labels_html = cmk.gui.view_utils.render_labels({label_id: label_value},
                                                       object_type,
                                                       with_links=False,
                                                       label_sources={})
        if not negate:
            return labels_html

        return HTML("%s%s" % (html.render_i(_("not"), class_="label_operator"), labels_html))

    def _host_conditions(self, conditions: RuleConditions) -> Generator:
        if conditions.host_name is None:
            return

        # Other cases should not occur, e.g. list of explicit hosts
        # plus watolib.ALL_HOSTS.
        condition_txt = self._render_host_condition_text(conditions)
        if condition_txt:
            yield condition_txt

    def _render_host_condition_text(self, conditions):
        if conditions.host_name == []:
            return _("This rule does <b>never</b> apply due to an empty list of explicit hosts!")

        condition: List[Union[HTML, str]] = []
        text_list: List[Union[HTML, str]] = []

        is_negate, host_name_conditions = ruleset_matcher.parse_negated_condition_list(
            conditions.host_name)

        regex_count = len(
            [x for x in host_name_conditions if isinstance(x, dict) and "$regex" in x])

        condition.append(_("Host name"))

        if regex_count == len(host_name_conditions) or regex_count == 0:
            # Entries are either complete regex or no regex at all
            is_regex = regex_count > 0
            if is_regex:
                condition.append(
                    _("is not one of regex") if is_negate else _("matches one of regex"))
            else:
                condition.append(_("is not one of") if is_negate else _("is"))

            for host_spec in host_name_conditions:
                if isinstance(host_spec, dict) and "$regex" in host_spec:
                    host_spec = host_spec["$regex"]

                if not is_regex:
                    host = watolib.Host.host(host_spec)
                    if host:
                        host_spec = html.render_a(host_spec, host.edit_url())

                text_list.append(html.render_b(host_spec))

        else:
            # Mixed entries
            for host_spec in host_name_conditions:
                is_regex = isinstance(host_spec, dict) and "$regex" in host_spec
                if is_regex:
                    host_spec = host_spec["$regex"]

                if not is_regex:
                    host = watolib.Host.host(host_spec)
                    if host:
                        host_spec = html.render_a(host_spec, host.edit_url())

                if is_negate:
                    expression = "%s" % (is_regex and _("does not match regex") or _("is not"))
                else:
                    expression = "%s" % (is_regex and _("matches regex") or _("is "))
                text_list.append("%s %s" % (expression, html.render_b(host_spec)))

        if len(text_list) == 1:
            condition.append(text_list[0])
        else:
            condition.append(", ".join(["%s" % s for s in text_list[:-1]]))
            condition.append(_(" or ") + text_list[-1])

        return HTML(" ").join(condition)

    def _service_conditions(self, rulespec: Rulespec, conditions: RuleConditions) -> Generator:
        if not rulespec.item_type or conditions.service_description is None:
            return

        condition = str()
        if rulespec.item_type == "service":
            condition = _("Service name")
        elif rulespec.item_type == "item":
            if rulespec.item_name is not None:
                condition = rulespec.item_name
            else:
                condition = _("Item")
        condition += " "

        is_negate, service_conditions = ruleset_matcher.parse_negated_condition_list(
            conditions.service_description)

        exact_match_count = len(
            [x for x in service_conditions if not isinstance(x, dict) or x["$regex"][-1] == "$"])

        text_list: List[Union[HTML, str]] = []
        if exact_match_count == len(service_conditions) or exact_match_count == 0:
            if is_negate:
                condition += exact_match_count == 0 and _("does not begin with ") or ("is not ")
            else:
                condition += exact_match_count == 0 and _("begins with ") or ("is ")

            for item_spec in service_conditions:
                is_regex = isinstance(item_spec, dict) and "$regex" in item_spec
                if is_regex:
                    item_spec = item_spec["$regex"]
                text_list.append(html.render_b(item_spec.rstrip("$")))
        else:
            for item_spec in service_conditions:
                is_regex = isinstance(item_spec, dict) and "$regex" in item_spec
                if is_regex:
                    item_spec = item_spec["$regex"]

                is_exact = item_spec[-1] == "$"
                if is_negate:
                    expression = "%s" % (is_exact and _("is not ") or _("begins not with "))
                else:
                    expression = "%s" % (is_exact and _("is ") or _("begins with "))
                text_list.append("%s%s" % (expression, html.render_b(item_spec.rstrip("$"))))

        if len(text_list) == 1:
            condition += ensure_str(render_html(text_list[0]))
        else:
            condition += ", ".join(["%s" % s for s in text_list[:-1]])
            condition += ensure_str(render_html(_(" or ") + text_list[-1]))

        if condition:
            yield condition


@mode_registry.register
class ModeEditRule(EditRuleMode):
    @classmethod
    def name(cls):
        return "edit_rule"

    @classmethod
    def permissions(cls):
        return []

    def _save_rule(self):
        # Just editing without moving to other folder
        self._ruleset.edit_rule(self._rule)
        self._rulesets.save()


@mode_registry.register
class ModeCloneRule(EditRuleMode):
    @classmethod
    def name(cls):
        return "clone_rule"

    @classmethod
    def permissions(cls):
        return []

    def title(self):
        return _("Copy rule: %s") % self._rulespec.title

    def _set_rule(self):
        super(ModeCloneRule, self)._set_rule()

        self._orig_rule = self._rule
        self._rule = self._orig_rule.clone()

    def _save_rule(self):
        if self._rule.folder == self._orig_rule.folder:
            self._ruleset.insert_rule_after(self._rule, self._orig_rule)
        else:
            self._ruleset.append_rule(self._rule.folder(), self._rule)

        self._rulesets.save()

    def _remove_from_orig_folder(self):
        pass  # Cloned rule is not yet in folder, don't try to remove


@mode_registry.register
class ModeNewRule(EditRuleMode):
    @classmethod
    def name(cls):
        return "new_rule"

    @classmethod
    def permissions(cls):
        return []

    def title(self):
        return _("New rule: %s") % self._rulespec.title

    def _set_folder(self):
        if html.request.has_var("_new_rule"):
            # Start creating new rule in the choosen folder
            self._folder = watolib.Folder.folder(
                html.request.get_ascii_input_mandatory("rule_folder"))

        elif html.request.has_var("_new_host_rule"):
            # Start creating new rule for a specific host
            self._folder = watolib.Folder.current()

        else:
            # Submitting the create dialog
            try:
                self._folder = watolib.Folder.folder(self._get_folder_path_from_vars())
            except MKUserError:
                # Folder can not be gathered from form if an error occurs
                self._folder = watolib.Folder.folder(html.request.var("rule_folder"))

    def _get_folder_path_from_vars(self):
        return self._get_rule_conditions_from_vars().host_folder

    def _set_rule(self):
        host_name_conditions: HostNameConditions = None
        service_description_conditions: ServiceNameConditions = None

        if html.request.has_var("_new_host_rule"):
            hostname = html.request.get_ascii_input("host")
            if hostname:
                host_name_conditions = [hostname]

            if self._rulespec.item_type:
                item = watolib.mk_eval(html.request.get_unicode_input_mandatory(
                    "item")) if html.request.has_var("item") else None
                if item is not None:
                    service_description_conditions = [{"$regex": "%s$" % escape_regex_chars(item)}]

        self._rule = watolib.Rule.create(self._folder, self._ruleset)
        self._rule.update_conditions(
            RuleConditions(
                host_folder=self._folder.path(),
                host_tags={},
                host_labels={},
                host_name=host_name_conditions,
                service_description=service_description_conditions,
                service_labels={},
            ))

    def _save_rule(self):
        self._ruleset.append_rule(self._folder, self._rule)
        self._rulesets.save()
        add_change("edit-rule",
                   _("Created new rule in ruleset \"%s\" in folder \"%s\"") %
                   (self._ruleset.title(), self._folder.alias_path()),
                   sites=self._folder.all_site_ids())

    def _success_message(self):
        return _("Created new rule in ruleset \"%s\" in folder \"%s\"") % \
                 (self._ruleset.title(),
                  self._folder.alias_path())
