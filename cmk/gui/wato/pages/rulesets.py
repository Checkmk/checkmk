#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO's awesome rule editor: Lets the user edit rule based parameters"""

from __future__ import annotations

import abc
import json
import re
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict
from enum import auto, Enum
from pprint import pformat
from typing import Any, cast, Final, Literal, NamedTuple, overload, TypedDict

from livestatus import SiteConfiguration

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.labels import LabelGroups
from cmk.utils.regex import escape_regex_chars
from cmk.utils.rulesets import ruleset_matcher
from cmk.utils.rulesets.conditions import (
    allow_host_label_conditions,
    allow_label_conditions,
    allow_service_label_conditions,
    HostOrServiceConditions,
    HostOrServiceConditionsSimple,
)
from cmk.utils.rulesets.definition import RuleGroup, RuleGroupType
from cmk.utils.rulesets.ruleset_matcher import (
    RulesetName,
    RuleSpec,
    TagCondition,
    TagConditionNE,
    TagConditionNOR,
    TagConditionOR,
)
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.tags import GroupedTag, TagGroupID, TagID

import cmk.gui.watolib.changes as _changes
from cmk.gui import deprecations, forms
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.form_specs.private import LegacyValueSpec
from cmk.gui.form_specs.vue.form_spec_visitor import (
    DisplayMode,
    parse_data_from_frontend,
    render_form_spec,
    RenderMode,
)
from cmk.gui.form_specs.vue.visitors import DataOrigin, DEFAULT_VALUE
from cmk.gui.hooks import call as call_hooks
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import mandatory_parameter, request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_confirmed_form_submit_link,
    make_form_submit_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
    search_form,
)
from cmk.gui.quick_setup.html import (
    quick_setup_duplication_warning,
    quick_setup_locked_warning,
    quick_setup_render_link,
    quick_setup_source_cell,
)
from cmk.gui.table import Foldable, show_row_count, Table, table_element
from cmk.gui.type_defs import ActionResult, HTTPVariables, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import escape_to_html_permissive, strip_tags
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    doc_reference_url,
    DocReference,
    make_confirm_delete_link,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListChoice,
    ListOfStrings,
    RegExp,
    rule_option_elements,
    Transform,
    Tuple,
    ValueSpec,
    ValueSpecText,
)
from cmk.gui.valuespec import LabelGroups as VSLabelGroups
from cmk.gui.view_utils import render_label_groups
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.automations import (
    LocalAutomationConfig,
    make_automation_config,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.check_mk_automations import (
    analyse_service,
    analyze_host_rule_effectiveness,
    analyze_host_rule_matches,
    analyze_service_rule_matches,
    find_unknown_check_parameter_rule_sets,
    get_check_information,
)
from cmk.gui.watolib.config_hostname import ConfigHostname
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_label_sync import execute_host_label_sync
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    folder_from_request,
    folder_lookup_cache,
    folder_preserving_link,
    folder_tree,
    Host,
    make_action_link,
)
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderPath,
    FolderRulesets,
    may_edit_ruleset,
    Rule,
    RuleConditions,
    RuleOptions,
    rules_grouped_by_folder,
    Ruleset,
    RulesetCollection,
    SearchOptions,
    SingleRulesetRecursively,
    UseHostFolder,
    visible_ruleset,
    visible_rulesets,
)
from cmk.gui.watolib.rulespecs import (
    FormSpecNotImplementedError,
    get_rulegroup,
    main_module_from_rulespec_group_name,
    MatchType,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
    RulespecSubGroup,
)
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.watolib.utils import mk_eval, mk_repr

from cmk import trace
from cmk.rulesets.v1.form_specs import FormSpec

from ._rule_conditions import DictHostTagCondition

_DEPRECATION_WARNING = "<b>This feature will be deprecated in a future version of Checkmk.</b>"
_OTEL_WARNING = (
    "The OpenTelemetry collector is an experimental beta feature, and not supported yet. "
    "Use and test at your heart's desire, just don’t rely on it in production - scope & features may change."
)
_OTEL_RULESPECS = [RuleGroup.SpecialAgents("otel"), RuleGroup.CheckgroupParameters("otel_metrics")]
tracer = trace.get_tracer()


def register(
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    mode_registry.register(ModeRuleSearch)
    mode_registry.register(ModeRulesetGroup)
    mode_registry.register(ModeEditRuleset)
    mode_registry.register(ModeRuleSearchForm)
    mode_registry.register(ModeEditRule)
    mode_registry.register(ModeCloneRule)
    mode_registry.register(ModeNewRule)
    mode_registry.register(ModeExportRule)
    mode_registry.register(ModeUnknownRulesets)
    match_item_generator_registry.register(MatchItemGeneratorUnknownRuleSets("unknown_rulesets"))


def _group_rulesets(
    rulesets: Iterable[Ruleset],
) -> list[tuple[str, list[tuple[str, list[Ruleset]]]]]:
    """Groups the rulesets in 3 layers (main group, sub group, rulesets)."""
    grouped_dict: dict[str, dict[str, list[Ruleset]]] = {}
    for ruleset in rulesets:
        main_group = grouped_dict.setdefault(ruleset.rulespec.main_group_name, {})
        group_rulesets = main_group.setdefault(ruleset.rulespec.group_name, [])
        group_rulesets.append(ruleset)

    grouped = []
    for main_group_name, sub_groups in grouped_dict.items():
        sub_group_list = []

        for group_name, group_rulesets in sub_groups.items():
            sub_group_list.append((group_name, group_rulesets))

        grouped.append((main_group_name, sub_group_list))

    return grouped


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

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["rulesets"]

    def __init__(self) -> None:
        super().__init__()
        self._page_type = self._get_page_type(self._search_options)

        self._title: str = ""
        self._help: str | None = None
        self._set_title_help_and_doc_reference()

    @abc.abstractmethod
    def _set_title_help_and_doc_reference(self) -> None:
        raise NotImplementedError()

    def _from_vars(self) -> None:
        #  Explicitly hide deprecated rulesets by default
        if not request.has_var("search_p_ruleset_deprecated"):
            request.set_var("search_p_ruleset_deprecated", DropdownChoice.option_id(False))
            request.set_var("search_p_ruleset_deprecated_USE", "on")

        self._group_name = self._group_name_from_vars()

        # Transform the search argument to the "rule search" arguments
        if request.has_var("search"):
            request.set_var("search_p_fulltext", request.get_str_input_mandatory("search"))
            request.set_var("search_p_fulltext_USE", "on")
            request.del_var("search")

        # Transform the folder argumen (from URL or bradcrumb) to the "rule search arguments
        if request.var("folder"):
            request.set_var(
                "search_p_rule_folder_0", DropdownChoice.option_id(request.var("folder"))
            )
            request.set_var("search_p_rule_folder_1", DropdownChoice.option_id(True))
            request.set_var("search_p_rule_folder_USE", "on")

        self._search_options: SearchOptions = ModeRuleSearchForm().search_options

    def _group_name_from_vars(self) -> str | None:
        # Transform group argument to the "rule search arguments"
        # Keeping this for compatibility reasons for the moment
        # This is either given via "group" parameter or via search (see blow)
        if request.has_var("group"):
            group_name = request.get_ascii_input_mandatory("group")
            request.set_var("search_p_ruleset_group", DropdownChoice.option_id(group_name))
            request.set_var("search_p_ruleset_group_USE", "on")
            request.del_var("group")

        if request.has_var("search_p_ruleset_group"):
            return _vs_ruleset_group().from_html_vars("search_p_ruleset_group")

        return None

    @abc.abstractmethod
    def _get_page_type(self, search_options: SearchOptions) -> PageType:
        raise NotImplementedError()

    @abc.abstractmethod
    def _rulesets(self) -> RulesetCollection:
        raise NotImplementedError()

    def title(self) -> str:
        return self._title

    def page(self) -> None:
        if self._help:
            html.help(self._help)

        # In case the user has filled in the search form, filter the rulesets by the given query
        if self._search_options:
            rulesets = AllRulesets(
                visible_rulesets(
                    {
                        name: ruleset
                        for name, ruleset in self._rulesets().get_rulesets().items()
                        if ruleset.matches_search_with_rules(
                            self._search_options, debug=active_config.debug
                        )
                    }
                )
            )
        else:
            rulesets = AllRulesets(visible_rulesets(self._rulesets().get_rulesets()))

        if self._page_type is PageType.RuleSearch and not html.form_submitted():
            return  # Do not show the result list when no query has been made

        html.open_div(class_="rulesets")

        grouped_rulesets = sorted(
            _group_rulesets(rulesets.get_rulesets().values()),
            key=lambda k_v: get_rulegroup(k_v[0]).title,
        )

        show_main_group_title = len(grouped_rulesets) > 1

        for main_group_name, sub_groups in grouped_rulesets:
            main_group_title = get_rulegroup(main_group_name).title

            for group_name, group_rulesets in sorted(
                sub_groups,
                key=lambda k_v: get_rulegroup(k_v[0]).title,
            ):
                group_title = get_rulegroup(group_name).title
                forms.header(
                    title=(
                        f"{main_group_title} > {group_title}"
                        if show_main_group_title
                        else group_title
                    )
                )
                forms.container()

                for ruleset in sorted(group_rulesets, key=lambda x: str(x.title())):
                    html.open_div(class_=["ruleset"], title=strip_tags(ruleset.help() or ""))
                    html.open_div(class_="text")

                    url_vars: HTTPVariables = [
                        ("mode", "edit_ruleset"),
                        ("varname", ruleset.name),
                        ("back_mode", self.name()),
                    ]
                    view_url = makeuri(request, url_vars)

                    html.a(
                        ruleset.title(),
                        href=view_url,
                        class_="nonzero" if ruleset.is_empty() else "zero",
                    )
                    html.span("." * 200, class_="dots")
                    html.close_div()

                    num_rules = ruleset.num_rules()
                    if ruleset.search_matching_rules:
                        num_rules_txt = "%d/%d" % (len(ruleset.search_matching_rules), num_rules)
                    else:
                        num_rules_txt = "%d" % num_rules

                    html.div(
                        num_rules_txt,
                        class_=["rulecount", "nonzero" if ruleset.is_empty() else "zero"],
                    )
                    html.close_div()
                forms.end()

        if not grouped_rulesets:
            if self._search_options:
                msg = _("There are no rule sets or rules matching your search.")
            else:
                msg = _("There are no rules defined in this folder.")

            html.div(msg, class_="info")

        html.close_div()


class ModeRuleSearch(ABCRulesetMode):
    @classmethod
    def name(cls) -> str:
        return "rule_search"

    def _get_page_type(self, search_options: dict[str, str]) -> PageType:
        if _is_deprecated_rulesets_page(search_options):
            return PageType.DeprecatedRulesets

        if _is_ineffective_rules_page(search_options):
            return PageType.IneffectiveRules

        if _is_used_rulesets_page(search_options):
            return PageType.UsedRulesets

        return PageType.RuleSearch

    def _rulesets(self) -> RulesetCollection:
        all_rulesets = AllRulesets.load_all_rulesets()
        if self._group_name == "static":
            return RulesetCollection(
                {
                    name: ruleset
                    for name, ruleset in all_rulesets.get_rulesets().items()
                    if ruleset.rulespec.main_group_name == "static"
                }
            )
        return all_rulesets

    def _set_title_help_and_doc_reference(self) -> None:
        if self._page_type is PageType.DeprecatedRulesets:
            self._title = _("Rule search: Deprecated rule sets")
            self._help = _(
                "Here you can see a list of all deprecated rule sets (which are not used by Checkmk anymore). If "
                "you have defined some rules here, you might have to migrate the rules to their successors. Please "
                "refer to the release notes or context help of the rule sets for details."
            )
            self._doc_references: dict[DocReference, str] = {
                DocReference.WATO_RULES_DEPCRECATED: _("Obsolete rule sets"),
            }

        elif self._page_type is PageType.IneffectiveRules:
            self._title = _("Rule search: Rule sets with ineffective rules")
            self._help = _(
                "The following rule sets contain rules that do not match to any of the existing hosts."
            )
            self._doc_references = {
                DocReference.WATO_RULES_INEFFECTIVE: _("Ineffective rules"),
            }

        elif self._page_type is PageType.UsedRulesets:
            self._title = _("Rule search: Used rule sets")
            self._help = _("Non-empty rule sets")
            self._doc_references = {
                DocReference.WATO_RULES_IN_USE: _("Rule sets in use"),
            }

        elif self._page_type is PageType.RuleSearch:
            self._title = _("Rule search")
            self._help = None
            self._doc_references = {
                DocReference.WATO_RULES: _("Host and service parameters"),
            }

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
                                _page_menu_entry_search_rules(
                                    self._search_options,
                                    mode=self.name(),
                                    page_type=self._page_type,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Predefined searches"),
                            entries=list(
                                _page_menu_entries_predefined_searches(
                                    self._group_name,
                                    self._page_type,
                                )
                            ),
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
            inpage_search=(
                PageMenuSearch(default_value=self._search_options.get("fulltext", ""))
                if self._page_type is not PageType.RuleSearch
                else None
            ),
        )
        _add_doc_references(menu, self._doc_references)
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield _page_menu_entry_predefined_conditions()

    def page(self) -> None:
        if self._page_type is PageType.RuleSearch and not request.has_var("filled_in"):
            search_form(
                title="%s: " % _("Quick search"),
                default_value=self._search_options.get("fulltext", ""),
            )
        super().page()

    def action(self) -> HTTPRedirect:
        forms.remove_unused_vars("search_p_rule", _is_var_to_delete)
        return redirect(makeuri(request, []))


def _add_doc_references(page_menu: PageMenu, doc_references: dict[DocReference, str]) -> None:
    for reference, title in doc_references.items():
        page_menu.add_doc_reference(title, reference)


def _is_var_to_delete(form_prefix: str, varname: str, value: str) -> bool:
    """
    Example for hosttags:
    'search_p_rule_hosttags_USE':'on'

    We have to keep auxtags, if not 'ignored':
    'search_p_rule_hosttags_auxtag_ip-v4': 'ignore'/'is'/'is not'

    and tags with an own tagvalue variable, if not 'ignored':
    'search_p_rule_hosttags_tag_address_family' : 'ignore'/'is'/'is not'
    'search_p_rule_hosttags_tagvalue_address_family' : 'ip-v4-only'

    We also keep folder:
    'search_p_rule_folder_USE' : 'on'
    'search_p_rule_folder_1' : '60a33e6cf5151f2d52eddae9685cfa270426aa89d8dbc7dfb854606f1d1a40fe'
    """
    if "_auxtag_" in varname and value != "ignore":
        return False

    if "_hosttags_tag_" in varname and value != "ignore":
        tagvalue_varname = "{}_hosttags_tagvalue_{}".format(
            form_prefix,
            varname.split("_hosttags_tag_")[1],
        )
        if request.var(tagvalue_varname):
            return False

    if "_hosttags_tagvalue_" in varname:
        tag_varname = "{}_hosttags_tag_{}".format(
            form_prefix, varname.split("_hosttags_tagvalue_")[1]
        )
        tag_value = request.var(tag_varname)
        if tag_value and tag_value != "ignore":
            return False

    if "_folder_" in varname:
        return False

    # We could be more specific here but that would mean that we have to
    # exclude the other ~ 14 options with "if x not in varname". So let's just
    # exclude all that are not explicit handled above and hope the tests secure that.
    if (
        "_auxtag_" not in varname
        and "_hosttags_tag_" not in varname
        and "_hosttags_tagvalue_" not in varname
    ):
        return False

    return True


def _page_menu_entries_predefined_searches(
    group: str | None, page_type: PageType
) -> Iterable[PageMenuEntry]:
    for search_title, search_emblem, search_term, search_type in [
        ("Used rulesets", "enable", "ruleset_used", PageType.UsedRulesets),
        ("Ineffective rules", "disable", "rule_ineffective", PageType.IneffectiveRules),
        ("Deprecated rules", "warning", "ruleset_deprecated", PageType.DeprecatedRulesets),
    ]:
        uri_params: list[tuple[str, None | int | str]] = [
            ("mode", "rule_search"),
            ("search_p_%s" % search_term, DropdownChoice.option_id(True)),
            ("search_p_%s_USE" % search_term, "on"),
        ]

        if search_type == PageType.DeprecatedRulesets:
            uri_params += [
                ("search", ""),
                ("filled_in", "search"),
            ]

        if group is not None:
            uri_params += [
                ("group", group),
                ("search_p_ruleset_group", DropdownChoice.option_id(group)),
                ("search_p_ruleset_group_USE", "on"),
            ]

        yield PageMenuEntry(
            title=search_title,
            icon_name={
                "icon": "rulesets",
                "emblem": search_emblem,
            },
            is_shortcut=search_type != page_type,
            item=make_simple_link(folder_preserving_link(uri_params)),
        )

    yield PageMenuEntry(
        title=_("Unknown rule sets"),
        icon_name={"icon": "rulesets", "emblem": "warning"},
        item=make_simple_link(makeuri_contextless(request, [("mode", "unknown_rulesets")])),
        is_shortcut=True,
    )


class ModeRulesetGroup(ABCRulesetMode):
    """Lists rulesets in a ruleset group"""

    @classmethod
    def name(cls) -> str:
        return "rulesets"

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, group: str, host: str, item: str, service: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _from_vars(self) -> None:
        super()._from_vars()
        if not self._group_name:
            raise MKUserError(None, _("The mandatory group name is missing"))

    def _topic_breadcrumb_item(self) -> Iterable[BreadcrumbItem]:
        """Return the BreadcrumbItem for the topic of this mode"""
        if self._group_name is None:
            raise MKGeneralException("Group name is not set")
        rule_group = get_rulegroup(self._group_name)
        main_module = main_module_from_rulespec_group_name(
            rule_group.main_group().name
            if isinstance(rule_group, RulespecSubGroup)
            else rule_group.name,
            main_module_registry,
        )
        yield BreadcrumbItem(
            title=main_module.topic.title,
            url=None,
        )
        yield from main_module.additional_breadcrumb_items()

    def _breadcrumb_url(self) -> str:
        assert self._group_name is not None
        return self.mode_url(group=self._group_name)

    def _get_page_type(self, search_options: dict[str, str]) -> PageType:
        return PageType.RulesetGroup

    def _rulesets(self) -> RulesetCollection:
        all_rulesets = AllRulesets.load_all_rulesets()
        if self._group_name == "static":
            return RulesetCollection(
                {
                    name: ruleset
                    for name, ruleset in all_rulesets.get_rulesets().items()
                    if ruleset.rulespec.main_group_name == "static"
                }
            )
        return all_rulesets

    def _set_title_help_and_doc_reference(self) -> None:
        if self._group_name is None:
            raise MKGeneralException("Group name is not set")
        rulegroup = get_rulegroup(self._group_name)
        self._title, self._help = (rulegroup.title, rulegroup.help)
        self._doc_references = (
            rulegroup.doc_references if isinstance(rulegroup, RulespecGroup) else {}
        )

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
            inpage_search=PageMenuSearch(default_value=self._search_options.get("fulltext", "")),
        )
        _add_doc_references(menu, self._doc_references)
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        if user.may("wato.hosts") or user.may("wato.seeall"):
            current_folder = folder_from_request(
                request.var("folder"), request.get_ascii_input("host")
            )
            yield PageMenuEntry(
                title=_("Hosts in folder: %s") % current_folder.title(),
                icon_name="folder",
                item=make_simple_link(current_folder.url()),
            )

            if request.get_ascii_input("host"):
                host_name = request.get_ascii_input_mandatory("host")
                yield PageMenuEntry(
                    title=_("Host properties of: %s") % host_name,
                    icon_name="folder",
                    item=make_simple_link(
                        folder_preserving_link([("mode", "edit_host"), ("host", host_name)])
                    ),
                )

        yield _page_menu_entry_predefined_conditions()

        yield _page_menu_entry_search_rules(
            self._search_options,
            "rulesets",
            self._page_type,
        )

        yield from _page_menu_entries_predefined_searches(self._group_name, self._page_type)


def _page_menu_entry_predefined_conditions() -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Predefined conditions"),
        icon_name="predefined_conditions",
        item=make_simple_link(
            folder_preserving_link(
                [
                    ("mode", "predefined_conditions"),
                ]
            )
        ),
    )


def _page_menu_entry_search_rules(
    search_options: SearchOptions, mode: str, page_type: PageType
) -> PageMenuEntry:
    is_searching = bool(search_options)
    # Don't highlight the button on "standard page" searches. Meaning the page calls
    # that are no searches from the users point of view because he did not fill the
    # search form, but clicked a link in the GUI
    if is_searching:
        search_keys = sorted(search_options.keys())
        if (
            search_keys == ["ruleset_deprecated", "ruleset_group"]
            or _is_deprecated_rulesets_page(search_options)
            or _is_ineffective_rules_page(search_options)
            or _is_used_rulesets_page(search_options)
        ):
            is_searching = False

    if is_searching:
        title = _("Refine search")
    else:
        title = _("Search")

    return PageMenuEntry(
        title=title,
        icon_name="search",
        item=make_simple_link(
            makeuri(
                request,
                [
                    ("mode", "rule_search_form"),
                    ("back_mode", mode),
                ],
                delvars=["filled_in"],
            )
        ),
        is_shortcut=page_type is PageType.RuleSearch and html.form_submitted(),
        is_suggested=page_type is PageType.RuleSearch and html.form_submitted(),
    )


def _is_deprecated_rulesets_page(search_options: SearchOptions) -> bool:
    return search_options.get("ruleset_deprecated") is True


def _is_ineffective_rules_page(search_options: SearchOptions) -> bool:
    return (
        search_options.get("ruleset_deprecated") is False
        and search_options.get("rule_ineffective") is True
    )


def _is_used_rulesets_page(search_options: SearchOptions) -> bool:
    return (
        search_options.get("ruleset_deprecated") is False
        and search_options.get("ruleset_used") is True
    )


class MatchState(TypedDict):
    matched: bool
    keys: set[str]


class RuleMatchResult(NamedTuple):
    title: str
    img: str


class ModeEditRuleset(WatoMode):
    related_page_menu_hooks: list[Callable[[str], Iterator[PageMenuEntry]]] = []

    @classmethod
    def name(cls) -> str:
        return "edit_ruleset"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def ensure_permissions(self) -> None:
        super().ensure_permissions()
        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this rule set."))
        if self._host:
            self._host.permissions.need_permission("read")

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeRulesetGroup

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, varname: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def breadcrumb(self) -> Breadcrumb:
        # To be able to calculate the breadcrumb with the ModeRulesetGroup as parent, we need to
        # ensure that the group identity is available.
        with request.stashed_vars():
            request.set_var("group", self._rulespec.main_group_name)
            return super().breadcrumb()

    def __init__(self) -> None:
        super().__init__()
        store = PredefinedConditionStore()
        self._predefined_conditions = store.filter_usable_entries(store.load_for_reading())

    def _from_vars(self) -> None:
        self._folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))

        self._name = request.get_ascii_input_mandatory("varname")
        self._back_mode = request.get_ascii_input_mandatory(
            "back_mode", request.get_ascii_input_mandatory("ruleset_back_mode", "rulesets")
        )
        self._item: ServiceName | None = None
        self._service: ServiceName | None = None

        # TODO: Clean this up. In which case is it used?
        # - The calculation for the service_description is not even correct, because it does not
        # take translations into account (see cmk.base.config.service_description()).
        check_command = request.get_ascii_input("check_command")
        if check_command:
            checks = get_check_information(debug=active_config.debug).plugin_infos
            if check_command.startswith("check_mk-"):
                check_command = check_command[9:]
                self._name = RuleGroup.CheckgroupParameters(checks[check_command].get("group", ""))
                descr_pattern = checks[check_command]["service_description"].replace("%s", "(.*)")
                matcher = re.search(
                    descr_pattern, request.get_str_input_mandatory("service_description")
                )
                if matcher:
                    try:
                        self._item = matcher.group(1)
                    except Exception:
                        pass
            elif check_command.startswith("check_mk_active-"):
                check_command = check_command[16:].split(" ")[0][:-1]
                self._name = RuleGroup.ActiveChecks(check_command)

        try:
            self._rulespec = rulespec_registry[self._name]
        except KeyError:
            raise MKUserError("varname", _('The ruleset "%s" does not exist.') % self._name)

        if not visible_ruleset(self._rulespec.name):
            raise MKUserError("varname", _('The ruleset "%s" does not exist.') % self._name)

        self._valuespec = self._rulespec.valuespec

        if not self._item:
            self._item = None
            if request.has_var("item"):
                try:
                    self._item = mk_eval(request.get_ascii_input_mandatory("item"))
                except Exception:
                    pass

        hostname = request.get_ascii_input("host")
        self._host: Host | None = None
        self._hostname: HostName | None = None
        if hostname:
            try:
                self._hostname = HostName(hostname)
            except ValueError:
                raise MKUserError("host", _("Invalid host name: %s") % hostname)
            host = self._folder.host(self._hostname)
            self._host = host
            if not self._host:
                raise MKUserError("host", _("The given host does not exist."))

        # The service argument is only needed for performing match testing of rules
        if not self._service:
            self._service = None
            if request.has_var("service"):
                try:
                    self._service = mk_eval(request.get_ascii_input_mandatory("service"))
                except Exception:
                    pass

        if self._hostname and self._rulespec.item_type == "item" and not self._service:
            raise MKUserError(
                "service", _('Unable to analyze matching, because "service" parameter is missing')
            )

        self._just_edited_rule_from_vars()

    # After actions like editing or moving a rule there is a rule that the user has been
    # working before. Focus this rule row again to make multiple actions with a single
    # rule easier to handle
    def _just_edited_rule_from_vars(self) -> None:
        if (folder := request.var("rule_folder")) is None or not request.has_var("rule_id"):
            self._just_edited_rule = None
            return

        rule_folder = folder_tree().folder(folder)
        rulesets = FolderRulesets.load_folder_rulesets(rule_folder)
        ruleset = rulesets.get(self._name)

        self._just_edited_rule = None

        # rule number relative to folder
        rule_id = request.get_ascii_input("rule_id")
        if rule_id is None:
            return

        try:
            self._just_edited_rule = ruleset.get_rule_by_id(rule_id)
        except KeyError:
            pass

    def _breadcrumb_url(self) -> str:
        return self.mode_url(varname=self._name)

    def title(self) -> str:
        assert self._rulespec.title is not None
        title = self._rulespec.title

        if self._hostname:
            title += _(" for host %s") % self._hostname
            if request.has_var("item") and self._rulespec.item_type:
                assert self._rulespec.item_name is not None
                title += _(" and %s '%s'") % (self._rulespec.item_name.lower(), self._item)

        return title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rules",
                    title=_("Rules"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add rule"),
                            entries=list(self._page_menu_entries_rules()),
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
        _add_doc_references(menu, self._rulespec.doc_references)
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield _page_menu_entry_predefined_conditions()

        yield PageMenuEntry(
            title=_("Rule search"),
            icon_name="search",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "rule_search")],
                )
            ),
        )

        if self._hostname:
            yield PageMenuEntry(
                title=_("Services"),
                icon_name="services",
                item=make_simple_link(
                    folder_preserving_link([("mode", "inventory"), ("host", self._hostname)])
                ),
            )

            if user.may("wato.rulesets"):
                yield PageMenuEntry(
                    title=_("Parameters"),
                    icon_name="rulesets",
                    item=make_simple_link(
                        folder_preserving_link(
                            [
                                ("mode", "object_parameters"),
                                ("host", self._hostname),
                                ("service", self._service or self._item),
                            ]
                        )
                    ),
                )

        for related_hook in ModeEditRuleset.related_page_menu_hooks:
            yield from related_hook(self._name)

        if self._name == "logwatch_rules":
            yield PageMenuEntry(
                title=_("Pattern analyzer"),
                icon_name="logwatch",
                item=make_simple_link(
                    folder_preserving_link(
                        [
                            ("mode", "pattern_editor"),
                            ("host", self._hostname),
                        ]
                    )
                ),
                is_shortcut=True,
                is_suggested=True,
            )

    def _page_menu_entries_rules(self) -> Iterable[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Add rule"),
            icon_name="new",
            item=make_form_submit_link(form_name="new_rule", button_name="_new_dflt_rule"),
            is_shortcut=True,
            is_suggested=True,
            # Suggested but not enabled: Make it obvious for the user that 'adding' is disabled.
            is_enabled=not self._rulespec.is_deprecated,
        )

        if self._hostname:
            title = _("Add rule for current host")
            if self._item is not None and self._rulespec.item_type:
                assert self._rulespec.item_name is not None
                title = _("Add rule for current host and %s") % self._rulespec.item_name.lower()

            yield PageMenuEntry(
                title=title,
                icon_name={"icon": "services_blue", "emblem": "rulesets"},
                item=make_form_submit_link(form_name="new_rule", button_name="_new_host_rule"),
                is_shortcut=True,
                is_suggested=True,
            )

        if not self._folder.is_root():
            yield PageMenuEntry(
                title=_("Add rule in folder %s") % self._folder.title(),
                icon_name={"icon": "folder_blue", "emblem": "rulesets"},
                item=make_form_submit_link(form_name="new_rule", button_name="_new_rule"),
                is_shortcut=True,
                is_suggested=True,
            )

    def action(self) -> ActionResult:
        back_url = self.mode_url(
            varname=self._name,
            host=self._hostname or "",
            item=mk_repr(self._item).decode(),
            service=mk_repr(self._service).decode(),
        )

        if not transactions.check_transaction():
            return redirect(back_url)

        folder = mandatory_parameter("folder", request.var("folder"))

        rule_folder = folder_tree().folder(request.get_str_input_mandatory("_folder", folder))
        rule_folder.permissions.need_permission("write")
        rulesets = FolderRulesets.load_folder_rulesets(rule_folder)
        ruleset = rulesets.get(self._name)

        try:
            # rule number relative to folder
            rule_id = request.get_ascii_input_mandatory("_rule_id")
            rule = ruleset.get_rule_by_id(rule_id)
        except (IndexError, TypeError, ValueError, KeyError):
            raise MKUserError(
                "_rule_id", _("You are trying to edit a rule which does not exist anymore.")
            )

        action = request.get_ascii_input_mandatory("_action")
        if action == "delete":
            if is_locked_by_quick_setup(rule.locked_by):
                raise MKUserError(None, _("Cannot delete rules that are managed by quick setup."))
            ruleset.delete_rule(rule)
        elif action == "move_to":
            target_idx = request.get_integer_input_mandatory("_index")
            if target_idx != ruleset.move_rule_to(rule, target_idx):
                flash(
                    _(
                        "This rule cannot be moved above rules that "
                        "are defined as part of a quick setup."
                    ),
                    msg_type="warning",
                )

        rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )
        return redirect(back_url)

    def page(self) -> None:
        if not active_config.wato_hide_varnames:
            display_varname = (
                '%s["%s"]' % tuple(self._name.split(":")) if ":" in self._name else self._name
            )
            html.div(display_varname, class_="varname")

        ruleset = SingleRulesetRecursively.load_single_ruleset_recursively(self._name).get(
            self._name
        )

        if self._rulespec.deprecation_planned:
            forms.warning_message(_DEPRECATION_WARNING)
        if self._rulespec.name in _OTEL_RULESPECS:
            forms.warning_message(_OTEL_WARNING)

        html.help(ruleset.help())
        self._explain_match_type(ruleset.match_type())
        self._rule_listing(ruleset, site_configs=active_config.sites, debug=active_config.debug)
        self._create_form()

    def _explain_match_type(self, match_type: MatchType) -> None:
        html.open_div(class_="matching_message")
        html.icon("toggle_details")
        html.b("%s: " % _("Matching"))

        match match_type:
            case "first":
                html.write_text_permissive(_("The first matching rule defines the parameter."))
            case "dict":
                html.write_text_permissive(
                    _(
                        "Each parameter is defined by the first matching rule where that "
                        "parameter is set (checked)."
                    )
                )
            case "varies":
                html.write_text_permissive(
                    _(
                        "The match type is defined by the discovery rule set type of the check plug-in."
                    )
                )
            case "all" | "list":
                html.write_text_permissive(_("All matching rules will add to the resulting list."))
            case _:
                html.write_text_permissive(_("Unknown match type: %s") % match_type)

        html.close_div()

    def _rule_listing(
        self, ruleset: Ruleset, *, site_configs: Mapping[SiteId, SiteConfiguration], debug: bool
    ) -> None:
        rules: list[tuple[Folder, int, Rule]] = ruleset.get_rules()
        if not rules:
            html.div(_("There are no rules defined in this set."), class_="info")
            return

        search_options: SearchOptions = ModeRuleSearchForm().search_options

        rule_effectiveness = (
            analyze_host_rule_effectiveness(
                [r.to_single_base_ruleset() for _f, _i, r in rules],
                debug=debug,
            ).results
            if "rule_ineffective" in search_options
            else {}
        )

        html.div("", id_="row_info")
        num_rows = 0

        rule_match_results = (
            self._analyze_rule_matching(
                self._host.site_id(),
                make_automation_config(site_configs[self._host.site_id()]),
                self._hostname,
                self._item,
                self._service,
                ruleset.rulespec,
                [e[2] for e in rules],
                debug=debug,
            )
            if self._hostname and self._host
            else {}
        )

        for folder, folder_rules in rules_grouped_by_folder(rules, self._folder):
            with table_element(
                f"rules_{self._name}_{folder.ident()}",
                title="%s %s (%d)"
                % (
                    _("Rules in folder"),
                    folder.alias_path(),
                    ruleset.num_rules_in_folder(folder),
                ),
                css="ruleset",
                searchable=False,
                sortable=False,
                limit=None,
                foldable=Foldable.FOLDABLE_SAVE_STATE,
                omit_update_header=True,
            ) as table:
                for _folder, rulenr, rule in folder_rules:
                    num_rows += 1
                    table.row(css=self._css_for_rule(search_options, rule))
                    self._set_focus(rule)
                    self._show_rule_icons(
                        table,
                        folder,
                        rule,
                        rulenr,
                        search_options,
                        rule_match_results,
                        rule_effectiveness,
                    )
                    self._rule_cells(table, rule)

        show_row_count(
            row_count=(row_count := num_rows),
            row_info=_("row") if row_count == 1 else _("rows"),
        )

    @staticmethod
    def _css_for_rule(search_options: SearchOptions, rule: Rule) -> list[str]:
        css = []
        if rule.is_disabled():
            css.append("disabled")
        return [" ".join(css)]

    def _set_focus(self, rule: Rule) -> None:
        if self._just_edited_rule and self._just_edited_rule.id == rule.id:
            html.focus_here()

    def _show_rule_icons(
        self,
        table: Table,
        folder: Folder,
        rule: Rule,
        rulenr: int,
        search_options: SearchOptions,
        rule_match_results: Mapping[str, RuleMatchResult],
        rule_effectiveness: dict[str, bool],
    ) -> None:
        if rule_match_results:
            table.cell(_("Match host"), css=["narrow"])
            result = rule_match_results[rule.id]
            html.icon(result.img, result.title)

        if rule.ruleset.has_rule_search_options(search_options):
            table.cell(_("Match search"), css=["narrow"])
            if rule.matches_search(search_options, rule_effectiveness) and (
                "fulltext" not in search_options
                or not rule.ruleset.matches_fulltext_search(search_options)
            ):
                if _is_ineffective_rules_page(search_options):
                    html.icon("hyphen", _("Ineffective rule"))
                else:
                    html.icon("checkmark_plus", _("Matches"))
            else:
                html.empty_icon()

        table.cell("#", css=["narrow nowrap"])
        html.write_text_permissive(rulenr)

        table.cell("", css=["buttons"])
        if rule.is_disabled():
            html.icon("disabled", _("This rule is currently disabled and will not be applied"))
        else:
            html.empty_icon()

        folder_preserving_vars = [
            ("ruleset_back_mode", self._back_mode),
            ("varname", self._name),
            ("rule_id", rule.id),
            ("host", self._hostname),
            ("item", mk_repr(self._item).decode()),
            ("service", mk_repr(self._service).decode()),
            ("rule_folder", folder.path()),
        ]

        table.cell(_("Actions"), css=["buttons rulebuttons"])
        edit_url = folder_preserving_link([("mode", "edit_rule"), *folder_preserving_vars])
        html.icon_button(edit_url, _("Edit this rule"), "edit")

        clone_url = folder_preserving_link([("mode", "clone_rule"), *folder_preserving_vars])
        html.icon_button(clone_url, _("Create a copy of this rule"), "clone")

        export_url = folder_preserving_link([("mode", "export_rule"), *folder_preserving_vars])
        html.icon_button(export_url, _("Export this rule for API"), "export_rule")

        if is_locked_by_quick_setup(rule.locked_by):
            html.icon_button(
                url="",
                title=_("Rule cannot be moved, because it is managed by quick setup"),
                icon="drag",
                class_=["disabled"],
            )
            html.icon_button(
                url="",
                title=_("Rule can only be deleted via quick setup"),
                icon="delete",
                class_=["disabled"],
            )

        else:
            html.element_dragger_url("tr", base_url=self._action_url("move_to", folder, rule.id))
            html.icon_button(
                url=make_confirm_delete_link(
                    url=self._action_url("delete", folder, rule.id),
                    title=_("Delete rule #%d") % rulenr,
                    suffix=rule.rule_options.description,
                    message=_("Folder: %s") % folder.alias_path(),
                ),
                title=_("Delete this rule"),
                icon="delete",
            )

    def _analyze_rule_matching(
        self,
        site_id: SiteId,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        host_name: HostName,
        item: Item,
        service_name: ServiceName | None,
        rulespec: Rulespec,
        rules: Sequence[Rule],
        *,
        debug: bool,
    ) -> dict[str, RuleMatchResult]:
        with tracer.span(
            "ModeEditRuleset_analyze_rule_matching",
            attributes={
                "cmk.gui.site_id": site_id,
                "cmk.gui.host_name": host_name,
                "cmk.gui.item": repr(item),
                "cmk.gui.service_name": repr(service_name),
            },
        ) as span:
            service_labels = (
                analyse_service(
                    automation_config,
                    host_name,
                    service_name,
                    debug=debug,
                ).labels
                if service_name
                else {}
            )
            span.set_attribute("cmk.service_labels", repr(service_labels))
            self._get_host_labels_from_remote_site(automation_config, debug=debug)

            if rulespec.is_for_services:
                rule_matches = {
                    rule_id: bool(matches)
                    for rule_id, matches in analyze_service_rule_matches(
                        host_name,
                        (service_name if rulespec.item_type == "service" else item) or "",
                        service_labels,
                        [r.to_single_base_ruleset() for r in rules],
                        debug=debug,
                    ).results.items()
                }
            else:
                rule_matches = {
                    rule_id: bool(matches)
                    for rule_id, matches in analyze_host_rule_matches(
                        host_name,
                        [r.to_single_base_ruleset() for r in rules],
                        debug=debug,
                    ).results.items()
                }

            span.set_attribute("cmk.gui.rule_matches", repr(rule_matches))

            match_state = MatchState({"matched": False, "keys": set()})
            return {
                rule.id: self._make_match_result(
                    match_state,
                    rule,
                    rule_matches[rule.id],
                    host_name,
                    item,
                )
                for rule in rules
            }

    def _make_match_result(
        self,
        match_state: MatchState,
        rule: Rule,
        rule_matches: bool,
        host_name: HostName,
        item: Item,
    ) -> RuleMatchResult:
        if rule.is_disabled():
            return RuleMatchResult(
                _("This rule does not match: %s") % _("This rule is disabled"), "hyphen"
            )

        if not rule_matches:
            return RuleMatchResult(
                _("This rule does not match: %s") % _("The rule does not match"), "hyphen"
            )

        ruleset = rule.ruleset
        if rule.ruleset.match_type() == "dict":
            new_keys = set(rule.value.keys())
            already_existing = match_state["keys"] & new_keys
            match_state["keys"] |= new_keys
            if not new_keys:
                return RuleMatchResult(
                    _("This rule matches, but does not define any parameters."),
                    "checkmark_orange",
                )
            if not already_existing:
                return RuleMatchResult(
                    _("This rule matches and defines new parameters."), "checkmark"
                )
            if already_existing == new_keys:
                return RuleMatchResult(
                    _(
                        "This rule matches, but all of its parameters are overridden by previous rules."
                    ),
                    "checkmark_orange",
                )
            return RuleMatchResult(
                _(
                    "This rule matches, but some of its parameters are overridden by previous rules."
                ),
                "checkmark_plus",
            )
        if match_state["matched"] and ruleset.match_type() != "all":
            return RuleMatchResult(
                _("This rule matches, but is overridden by a previous rule."),
                "checkmark_orange",
            )
        match_state["matched"] = True
        return RuleMatchResult(
            (_("This rule matches for the host '%s'") % host_name)
            + (
                _(" and the %s '%s'.") % (ruleset.item_name(), item) if ruleset.item_type() else "."
            ),
            "checkmark",
        )

    def _get_host_labels_from_remote_site(
        self, automation_config: LocalAutomationConfig | RemoteAutomationConfig, *, debug: bool
    ) -> None:
        """To be able to execute the match simulation we need the discovered host labels to be
        present in the central site. Fetch and store them."""
        if not self._hostname:
            return

        if isinstance(automation_config, LocalAutomationConfig):
            return

        # Labels should only get synced once per request
        cache_id = f"{automation_config.site_id}:{self._hostname}"
        if cache_id in g.get("host_label_sync", {}):
            return
        execute_host_label_sync(self._hostname, automation_config, debug=debug)
        g.setdefault("host_label_sync", {})[cache_id] = True

    def _action_url(self, action: str, folder: Folder, rule_id: str) -> str:
        vars_: HTTPVariables = [
            ("mode", request.var("mode", "edit_ruleset")),
            ("ruleset_back_mode", self._back_mode),
            ("varname", self._name),
            ("_folder", folder.path()),
            ("_rule_id", rule_id),
            ("_action", action),
        ]
        if request.var("rule_folder"):
            vars_.append(("rule_folder", folder.path()))
        if self._hostname:
            vars_.append(("host", self._hostname))
        if self._item:
            vars_.append(("item", mk_repr(self._item).decode()))
        if self._service:
            vars_.append(("service", mk_repr(self._service).decode()))

        return make_action_link(vars_)

    # TODO: Refactor this whole method
    def _rule_cells(
        self,
        table: Table,
        rule: Rule,
    ) -> None:
        value = rule.value
        rule_options = rule.rule_options

        # Conditions
        table.cell(_("Conditions"), css=["condition"])
        self._rule_conditions(rule)

        # Value
        table.cell(_("Value"), css=["value"])

        def _show_rule_backend():
            try:
                value_html = self._valuespec.value_to_html(value)
            except Exception as e:
                try:
                    reason = str(e)
                    self._valuespec.validate_datatype(value, "")
                except Exception as e2:
                    reason = str(e2)

                value_html = (
                    html.render_icon("alert")
                    + HTML.with_escaping(_("The value of this rule is not valid. "))
                    + escape_to_html_permissive(reason)
                )
            html.write_text_permissive(value_html)

        def _show_rule_frontend(form_spec: FormSpec) -> None:
            render_form_spec(
                form_spec,
                rule.id,
                value,
                DataOrigin.DISK,
                True,
                display_mode=DisplayMode.READONLY,
            )

        render_mode, form_spec = _get_render_mode(self._rulespec)
        match render_mode:
            case RenderMode.BACKEND:
                _show_rule_backend()
            case RenderMode.FRONTEND:
                assert form_spec is not None
                _show_rule_frontend(form_spec)
            case RenderMode.FRONTEND | RenderMode.BACKEND_AND_FRONTEND:
                assert form_spec is not None
                _show_rule_frontend(form_spec)
                # html.write_html("<hr>")
                # _show_rule_backend()

        # Comment
        table.cell(_("Description"), css=["description"])
        if docu_url := rule_options.docu_url:
            html.icon_button(
                docu_url,
                _("Context information about this rule"),
                "url",
                target="_blank",
            )
            html.write_text_permissive("&nbsp;")

        desc = rule.rule_options.description or rule.rule_options.comment or ""
        html.write_text_permissive(desc)

        quick_setup_source_cell(table, rule.locked_by)

    def _rule_conditions(self, rule: Rule) -> None:
        self._predefined_condition_info(rule)
        html.write_text_permissive(
            VSExplicitConditions(rulespec=self._rulespec, render="normal").value_to_html(
                rule.get_rule_conditions()
            )
        )

    def _predefined_condition_info(self, rule: Rule) -> None:
        condition_id = rule.predefined_condition_id()
        if condition_id is None:
            return

        condition = self._predefined_conditions.get(condition_id)
        if condition is None:
            html.write_text_permissive(
                _("Predefined condition: '%s' does not exist or using not permitted") % condition_id
            )
            return

        url = folder_preserving_link(
            [
                ("mode", "edit_predefined_condition"),
                ("ident", condition_id),
            ]
        )
        html.write_text_permissive(
            _('Predefined condition: <a href="%s">%s</a>') % (url, condition["title"])
        )

    def _create_form(self) -> None:
        with html.form_context("new_rule", add_transid=False):
            html.hidden_field("ruleset_back_mode", self._back_mode, add_var=True)

            if self._hostname:
                html.hidden_field("host", self._hostname)
                html.hidden_field("item", mk_repr(self._item).decode())
                html.hidden_field("service", mk_repr(self._service).decode())

            html.hidden_field("rule_folder", self._folder.path())
            html.hidden_field("varname", self._name)
            html.hidden_field("mode", "new_rule")
            html.hidden_field("folder", self._folder.path())


class ModeRuleSearchForm(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "rule_search_form"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["rulesets"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeRuleSearch

    def __init__(self) -> None:
        self.back_mode = request.get_ascii_input_mandatory("back_mode", "rulesets")
        super().__init__()

    def title(self) -> str:
        if self.search_options:
            return _("Refine search")
        return _("Search rulesets and rules")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Search"),
            breadcrumb,
            form_name="rule_search",
            button_name="_do_search",
            save_title=_("Search"),
        )
        action_topic = menu.dropdowns[0].topics[0]
        action_topic.entries.insert(
            1,
            PageMenuEntry(
                title=_("Reset"),
                icon_name="reset",
                item=make_form_submit_link("rule_search", "_reset_search"),
                is_shortcut=True,
                is_suggested=True,
            ),
        )
        return menu

    def page(self) -> None:
        with html.form_context("rule_search", method="POST"):
            html.hidden_field("mode", self.back_mode, add_var=True)

            valuespec = self._valuespec()
            valuespec.render_input_as_form("search", self.search_options)

            html.hidden_fields()

    def _from_vars(self) -> None:
        if request.var("_reset_search"):
            request.del_vars("search_")
            self.search_options: SearchOptions = {}
            return

        forms.remove_unused_vars("search_p_rule", _is_var_to_delete)
        value = self._valuespec().from_html_vars("search")
        self._valuespec().validate_value(value, "search")

        # In case all checkboxes are unchecked, treat this like the reset search button press
        # and remove all vars
        if not value:
            request.del_vars("search_")

        self.search_options = value

    def _valuespec(self) -> Dictionary:
        return Dictionary(
            title=_("Search rulesets"),
            headers=[
                (
                    _("Fulltext search"),
                    [
                        "fulltext",
                    ],
                ),
                (
                    _("Rulesets"),
                    [
                        "ruleset_group",
                        "ruleset_name",
                        "ruleset_title",
                        "ruleset_help",
                        "ruleset_deprecated",
                        "ruleset_used",
                    ],
                ),
                (
                    _("Rules"),
                    [
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
                    ],
                ),
            ],
            elements=[
                (
                    "fulltext",
                    RegExp(
                        title=_("Rules matching pattern"),
                        help=_(
                            "Use this field to search the description, comment, host and "
                            "service conditions including the text representation of the "
                            "configured values."
                        ),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                ("ruleset_group", _vs_ruleset_group()),
                (
                    "ruleset_name",
                    RegExp(
                        title=_("Name"),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "ruleset_title",
                    RegExp(
                        title=_("Title"),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "ruleset_help",
                    RegExp(
                        title=_("Help"),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "ruleset_deprecated",
                    DropdownChoice(
                        title=_("Deprecated"),
                        choices=[
                            (True, _("Search for deprecated rulesets")),
                            (False, _("Search for not deprecated rulesets")),
                        ],
                    ),
                ),
                (
                    "ruleset_used",
                    DropdownChoice(
                        title=_("Used"),
                        choices=[
                            (True, _("Search for rulesets that have rules configured")),
                            (False, _("Search for rulesets that don't have rules configured")),
                        ],
                    ),
                ),
                (
                    "rule_description",
                    RegExp(
                        title=_("Description"),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "rule_comment",
                    RegExp(
                        title=_("Comment"),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "rule_value",
                    RegExp(
                        title=_("Value"),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "rule_host_list",
                    RegExp(
                        title=_("Explicit host matching"),
                        help=_(
                            "Use this field to search for rules which have their "
                            "explicit host condition set up in such a way that it"
                            " matches the given host (either by being unset or "
                            "set)."
                        ),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "rule_item_list",
                    RegExp(
                        title=_("Explicit item matching"),
                        help=_(
                            "Use this field to search for rules which have their "
                            "item condition set up in such a way that it matches "
                            "the given item (either by being unset or set). The "
                            "item condition name depends on the rule, the item is"
                            " always part of the service name."
                        ),
                        size=60,
                        mode=RegExp.infix,
                    ),
                ),
                (
                    "rule_hosttags",
                    DictHostTagCondition(title=_("Used host tags"), help_txt=""),
                ),
                (
                    "rule_disabled",
                    DropdownChoice(
                        title=_("Disabled"),
                        choices=[
                            (True, _("Search for disabled rules")),
                            (False, _("Search for enabled rules")),
                        ],
                    ),
                ),
                (
                    "rule_ineffective",
                    DropdownChoice(
                        title=_("Ineffective"),
                        choices=[
                            (
                                True,
                                _(
                                    "Search for ineffective rules (not matching any host or service)"
                                ),
                            ),
                            (False, _("Search for effective rules")),
                        ],
                    ),
                ),
                (
                    "rule_folder",
                    Tuple(
                        title=_("Folder"),
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("Selection"),
                                choices=folder_tree().folder_choices,
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
                    ),
                ),
                (
                    "rule_predefined_condition",
                    DropdownChoice(
                        title=_("Using predefined condition"),
                        choices=PredefinedConditionStore().choices(),
                        sorted=True,
                    ),
                ),
            ],
        )


def _vs_ruleset_group() -> DropdownChoice:
    return DropdownChoice(
        title=_("Group"),
        choices=rulespec_group_registry.get_group_choices,
    )


def render_hidden_if_locked(vs: ValueSpec, varprefix: str, value: object, locked: bool) -> None:
    if locked:
        html.write_html(HTML.without_escaping(vs.value_to_html(value)))
        html.open_div(style="display:none;")

    vs.render_input(varprefix, value)

    if locked:
        html.close_div()


def _get_render_mode(rulespec: Rulespec) -> tuple[RenderMode, FormSpec | None]:
    configured_mode = _get_rule_render_mode()
    if configured_mode == RenderMode.BACKEND:
        return configured_mode, None

    try:
        return configured_mode, rulespec.form_spec
    except FormSpecNotImplementedError:
        pass

    return configured_mode, LegacyValueSpec(valuespec=rulespec.valuespec)


class ABCEditRuleMode(WatoMode):
    VAR_RULE_SPEC_NAME: Final = "varname"
    VAR_RULE_ID: Final = "rule_id"

    def __init__(self):
        self._do_validate_on_render = False
        super().__init__()

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def ensure_permissions(self) -> None:
        super().ensure_permissions()
        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditRuleset

    def _from_vars(self) -> None:
        self._name = request.get_ascii_input_mandatory(self.VAR_RULE_SPEC_NAME)

        try:
            self._rulespec = rulespec_registry[self._name]
        except KeyError:
            raise MKUserError(
                self.VAR_RULE_SPEC_NAME, _('The ruleset "%s" does not exist.') % self._name
            )

        self._back_mode = request.get_ascii_input_mandatory("back_mode", "edit_ruleset")

        self._set_folder()

        self._rulesets = FolderRulesets.load_folder_rulesets(self._folder)
        self._ruleset = self._rulesets.get(self._name)

        self._set_rule()

    def _set_folder(self) -> None:
        """Determine the folder object of the requested rule

        In case it is possible the call sites should set the folder. This makes loading the page
        much faster, because we not have to read all rules.mk files from all folders to find the
        correct folder. But in some cases (e.g. audit log), it is not possible to find the folder
        when linking to this page (for performance reasons in the audit log).
        """
        rule_folder = request.get_ascii_input("rule_folder")
        if rule_folder:
            self._folder = folder_tree().folder(rule_folder)
        else:
            rule_id = request.get_ascii_input_mandatory(self.VAR_RULE_ID)

            collection = SingleRulesetRecursively.load_single_ruleset_recursively(self._name)
            ruleset = collection.get(self._name)
            try:
                self._folder = ruleset.get_rule_by_id(rule_id).folder
            except KeyError:
                raise MKUserError(
                    self.VAR_RULE_ID,
                    _("You are trying to edit a rule which does not exist anymore."),
                )

    def _set_rule(self) -> None:
        if request.has_var(self.VAR_RULE_ID):
            try:
                rule_id = request.get_ascii_input_mandatory(self.VAR_RULE_ID)
                self._rule = self._ruleset.get_rule_by_id(rule_id)
            except (KeyError, TypeError, ValueError, IndexError):
                raise MKUserError(
                    self.VAR_RULE_ID,
                    _("You are trying to edit a rule which does not exist anymore."),
                )
        else:
            raise NotImplementedError()

        self._orig_rule = self._rule
        self._rule = self._orig_rule.clone(preserve_id=True)

    def title(self) -> str:
        return _("Edit rule: %s") % self._rulespec.title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Rule"),
            breadcrumb,
            form_name="rule_editor",
            button_name="_save",
            add_cancel_link=True,
            cancel_url=self._back_url(),
        )

        if this_rule_topic := self._page_menu_topic_this_rule():
            menu.dropdowns[0].topics.append(this_rule_topic)

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
            ),
        )

        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield _page_menu_entry_predefined_conditions()

    def _page_menu_topic_this_rule(self) -> PageMenuTopic | None:
        if user.may("wato.auditlog"):
            return PageMenuTopic(
                title=_("This rule"),
                entries=[
                    PageMenuEntry(
                        title=_("Audit log"),
                        icon_name="auditlog",
                        item=make_simple_link(make_object_audit_log_url(self._rule.object_ref())),
                    ),
                ],
            )
        return None

    def breadcrumb(self) -> Breadcrumb:
        # Let the ModeRulesetGroup know the group we are currently editing
        with request.stashed_vars():
            request.set_var("group", self._ruleset.rulespec.main_group_name)
            return super().breadcrumb()

    def _back_url(self) -> str:
        # TODO: Is this still needed + for which case?
        if self._back_mode == "edit_ruleset":
            var_list: HTTPVariables = [
                ("mode", "edit_ruleset"),
                (self.VAR_RULE_SPEC_NAME, self._name),
                ("host", request.get_ascii_input_mandatory("host", "")),
            ]
            if request.has_var("item"):
                var_list.append(("item", request.get_str_input_mandatory("item")))
            if request.has_var("service"):
                var_list.append(("service", request.get_str_input_mandatory("service")))
            return folder_preserving_link(var_list)

        return folder_preserving_link(
            [("mode", self._back_mode), ("host", request.get_ascii_input_mandatory("host", ""))]
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(self._back_url())

        if redirect_ := self._update_rule_from_vars():
            return redirect_

        # Check permissions on folders
        new_rule_folder = folder_tree().folder(self._get_rule_conditions_from_vars().host_folder)
        if not isinstance(self, ModeNewRule | ModeCloneRule):
            self._folder.permissions.need_permission("write")
        new_rule_folder.permissions.need_permission("write")

        if new_rule_folder == self._folder:
            self._rule.folder = new_rule_folder
            self._save_rule()

        elif is_locked_by_quick_setup(self._rule.locked_by):
            flash(_("Cannot change folder of rules managed by Quick setup."), msg_type="error")
            return redirect(self._back_url())

        else:
            # Move rule to new folder during editing
            self._remove_from_orig_folder()

            # Set new folder
            self._rule.folder = new_rule_folder

            self._rulesets = FolderRulesets.load_folder_rulesets(new_rule_folder)
            self._ruleset = self._rulesets.get(self._name)
            self._ruleset.append_rule(new_rule_folder, self._rule)
            self._rulesets.save_folder(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )

            affected_sites = list(set(self._folder.all_site_ids() + new_rule_folder.all_site_ids()))
            _changes.add_change(
                action_name="edit-rule",
                text=_('Changed properties of rule "%s", moved rule from folder "%s" to "%s"')
                % (self._ruleset.title(), self._folder.alias_path(), new_rule_folder.alias_path()),
                user_id=user.id,
                sites=affected_sites,
                diff_text=self._ruleset.diff_rules(self._orig_rule, self._rule),
                object_ref=self._rule.object_ref(),
                use_git=active_config.wato_use_git,
            )

        flash(self._success_message())
        return redirect(self._back_url())

    def _update_rule_from_vars(self) -> HTTPRedirect | None:
        # Additional options
        rule_options = self._vs_rule_options(self._rule).from_html_vars("options")
        self._vs_rule_options(self._rule).validate_value(rule_options, "options")

        self._rule.rule_options = RuleOptions(
            disabled=rule_options["disabled"],
            description=rule_options["description"],
            comment=rule_options["comment"],
            docu_url=rule_options["docu_url"],
        )

        # CONDITION
        rule_conditions = self._get_rule_conditions_from_vars()
        if (
            is_locked_by_quick_setup(self._rule.locked_by)
            and self._rule.conditions != rule_conditions
        ):
            flash(
                _("Cannot change rule conditions for rules managed by Quick setup."),
                msg_type="error",
            )
            return redirect(self._back_url())

        if self._get_condition_type_from_vars() == "predefined":
            condition_id = self._get_condition_id_from_vars()
            self._rule.rule_options.predefined_condition_id = condition_id

        self._rule.update_conditions(rule_conditions)

        # VALUE
        render_mode, registered_form_spec = _get_render_mode(self._ruleset.rulespec)
        self._do_validate_on_render = True
        match render_mode:
            case RenderMode.FRONTEND | RenderMode.BACKEND_AND_FRONTEND:
                assert registered_form_spec is not None
                value = parse_data_from_frontend(
                    registered_form_spec,
                    self._vue_field_id(),
                )
            case RenderMode.BACKEND:
                value = self._ruleset.valuespec().from_html_vars("ve")
                self._ruleset.valuespec().validate_value(value, "ve")

        self._rule.value = value
        return None

    def _get_condition_type_from_vars(self) -> str | None:
        condition_type = self._vs_condition_type().from_html_vars("condition_type")
        self._vs_condition_type().validate_value(condition_type, "condition_type")
        return condition_type

    # TODO: refine type
    def _get_condition_id_from_vars(self) -> Any:
        condition_id = self._vs_predefined_condition_id().from_html_vars("predefined_condition_id")
        self._vs_predefined_condition_id().validate_value(condition_id, "predefined_condition_id")
        return condition_id

    def _get_rule_conditions_from_vars(self) -> RuleConditions:
        if self._get_condition_type_from_vars() == "predefined":
            return self._get_predefined_rule_conditions(self._get_condition_id_from_vars())
        return self._get_explicit_rule_conditions()

    # TODO: refine type
    def _get_predefined_rule_conditions(self, condition_id: Any) -> RuleConditions:
        store = PredefinedConditionStore()
        store_entries = store.filter_usable_entries(store.load_for_reading())
        return RuleConditions(**store_entries[condition_id]["conditions"])

    @abc.abstractmethod
    def _save_rule(self) -> None:
        raise NotImplementedError()

    def _remove_from_orig_folder(self) -> None:
        self._ruleset.delete_rule(self._orig_rule, create_change=False)
        self._rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )

    def _success_message(self) -> str:
        return _('Edited rule in ruleset "%s" in folder "%s"') % (
            self._ruleset.title(),
            self._folder.alias_path(),
        )

    # TODO: refine type
    def _get_explicit_rule_conditions(self) -> Any:
        vs = self._vs_explicit_conditions(render="normal")
        conditions = vs.from_html_vars("explicit_conditions")
        vs.validate_value(conditions, "explicit_conditions")
        return conditions

    def _vue_field_id(self) -> str:
        # Note: this _underscore is critical because of the hidden vars special behaviour
        # Non _ vars are always added as hidden vars into a form
        return "_vue_edit_rule"

    def page(self) -> None:
        call_hooks("rmk_ruleset_banner", self._ruleset.name)

        help_text = self._ruleset.help()

        if self._rulespec.deprecation_planned:
            forms.warning_message(
                _DEPRECATION_WARNING + "<br>" + str(help_text)
                if help_text
                else _DEPRECATION_WARNING
            )
        elif help_text:
            html.div(help_text, class_="info")

        with html.form_context("rule_editor", method="POST"):
            self._page_form(debug=active_config.debug)

    def _get_rule_value_and_origin(self) -> tuple[Any, DataOrigin]:
        if request.has_var(self._vue_field_id()):
            return (
                json.loads(request.get_str_input_mandatory(self._vue_field_id())),
                DataOrigin.FRONTEND,
            )
        return self._rule.value, DataOrigin.DISK

    @property
    def folder(self) -> Folder:
        return self._folder

    @property
    def rule(self) -> Rule:
        return self._rule

    def _page_form_quick_setup_warning(self) -> None:
        if (
            is_locked_by_quick_setup(self._rule.locked_by)
            and request.get_ascii_input("mode") != "edit_configuration_bundle"
        ):
            quick_setup_locked_warning(self._rule.locked_by, "rule")

    def _should_validate_on_render(self) -> bool:
        return self._do_validate_on_render or not isinstance(self, ModeNewRule)

    def _page_form(self, *, debug: bool) -> None:
        self._page_form_quick_setup_warning()

        # Additional rule options
        self._vs_rule_options(self._rule).render_input("options", asdict(self._rule.rule_options))

        # Value
        valuespec = self._ruleset.valuespec()
        forms.header(
            valuespec.title() or _("Value"),
            show_more_toggle=valuespec.has_show_more(),
        )
        forms.section()
        html.form_has_submit_button = True
        html.prevent_password_auto_completion()
        try:
            render_mode, registered_form_spec = _get_render_mode(self._ruleset.rulespec)
            match render_mode:
                case RenderMode.BACKEND:
                    valuespec.validate_datatype(self._rule.value, "ve")
                    valuespec.render_input("ve", self._rule.value)
                case RenderMode.FRONTEND:
                    assert registered_form_spec is not None
                    value, origin = self._get_rule_value_and_origin()
                    render_form_spec(
                        registered_form_spec,
                        self._vue_field_id(),
                        value,
                        origin,
                        self._should_validate_on_render(),
                    )
                case RenderMode.BACKEND_AND_FRONTEND:
                    forms.section("Current setting as VUE")
                    assert registered_form_spec is not None
                    value, origin = self._get_rule_value_and_origin()
                    render_form_spec(
                        registered_form_spec,
                        self._vue_field_id(),
                        value,
                        origin,
                        self._should_validate_on_render(),
                    )
                    forms.section("Backend rendered (read only)")
                    valuespec.validate_datatype(self._rule.value, "ve")
                    valuespec.render_input("ve", self._rule.value)
        except Exception as e:
            if debug:
                raise
            html.show_warning(
                _(
                    "Unable to read current options of this rule. Falling back to "
                    "default values. When saving this rule now, your previous settings "
                    "will be overwritten. The problem was: %s."
                )
                % e
            )

            # In case of validation problems render the input with default values
            valuespec.render_input("ve", valuespec.default_value())

        valuespec.set_focus("ve")

        self._show_conditions()

        forms.end()

        html.hidden_fields()
        self._vs_rule_options(self._rule).set_focus("options")

    def _show_conditions(self) -> None:
        locked = is_locked_by_quick_setup(self._rule.locked_by)
        forms.header(_("Conditions"), css="locked" if locked else None)
        if locked:
            forms.warning_message(
                _("Conditions of rules managed by Quick setup cannot be changed.")
            )

        condition_type = "predefined" if self._rule.predefined_condition_id() else "explicit"

        forms.section(_("Condition type"))

        render_hidden_if_locked(self._vs_condition_type(), "condition_type", condition_type, locked)
        self._show_predefined_conditions(locked)
        self._show_explicit_conditions(locked)

        if not locked:
            html.javascript('cmk.wato.toggle_rule_condition_type("condition_type")')

    def _vs_condition_type(self) -> DropdownChoice[str]:
        return DropdownChoice(
            title=_("Condition type"),
            help=_(
                "You can either specify individual conditions for this rule, or use a set of "
                "predefined conditions, which may be handy if you have to configure the "
                "same conditions in different rulesets."
            ),
            choices=[
                ("explicit", _("Explicit conditions")),
                ("predefined", _("Predefined conditions")),
            ],
            on_change='cmk.wato.toggle_rule_condition_type("condition_type")',
            encode_value=False,
        )

    def _show_predefined_conditions(self, locked: bool) -> None:
        forms.section(_("Predefined condition"), css="condition predefined", hide=locked)
        render_hidden_if_locked(
            vs=self._vs_predefined_condition_id(),
            varprefix="predefined_condition_id",
            value=self._rule.predefined_condition_id(),
            locked=locked,
        )

    def _vs_predefined_condition_id(self) -> DropdownChoice:
        url = folder_preserving_link([("mode", "predefined_conditions")])
        return DropdownChoice[str](
            title=_("Predefined condition"),
            choices=PredefinedConditionStore().choices(),
            sorted=True,
            invalid_choice="complain",
            invalid_choice_title=_(
                "Predefined condition '%s' does not exist or using not permitted"
            ),
            invalid_choice_error=_(
                "The configured predefined condition has either be removed or you "
                "are not permitted to use it. Please choose another one."
            ),
            empty_text=(
                _("There are no elements defined for this selection yet.")
                + " "
                + _('You can create predefined conditions <a href="%s">here</a>.') % url
            ),
            validate=self._validate_predefined_condition,
        )

    # TODO: refine type
    def _validate_predefined_condition(self, value: str | None, varprefix: str) -> None:
        if allow_label_conditions(self._rulespec.name):
            return

        conditions = self._get_predefined_rule_conditions(value)
        if (
            conditions.host_label_groups and not allow_host_label_conditions(self._rulespec.name)
        ) or (
            conditions.service_label_groups
            and not allow_service_label_conditions(self._rulespec.name)
        ):
            raise MKUserError(
                varprefix,
                _(
                    "This predefined condition can not be used with the "
                    "current ruleset, because it defines the same label "
                    "conditions as set by this rule."
                ),
            )

    def _show_explicit_conditions(self, locked: bool) -> None:
        if locked:
            forms.section(_("Explicit condition"), css="condition explicit")
        vs = self._vs_explicit_conditions(render="normal" if locked else "form_part")
        value = self._rule.get_rule_conditions()

        try:
            vs.validate_datatype(value, "explicit_conditions")
            render_hidden_if_locked(vs, "explicit_conditions", value, locked)
        except Exception as e:
            forms.section("", css="condition explicit")
            html.show_warning(
                _(
                    "Unable to read current conditions of this rule. Falling back to "
                    "default values. When saving this rule now, your previous settings "
                    "will be overwritten. The problem was: %s, Previous conditions: <pre>%s</pre>"
                    "Such an issue may be caused by an inconsistent configuration, e.g. when "
                    "rules refer to tag groups or tags that do not exist anymore."
                )
                % (e, value.to_config(UseHostFolder.HOST_FOLDER_FOR_UI))
            )

            # In case of validation problems render the input with default values
            value = RuleConditions(host_folder=self._folder.path())
            render_hidden_if_locked(vs, "explicit_conditions", value, locked)

    def _vs_explicit_conditions(
        self, render: Literal["normal", "form_part"]
    ) -> VSExplicitConditions:
        return VSExplicitConditions(rulespec=self._rulespec, render=render)

    def _vs_rule_options(self, rule: Rule, disabling: bool = True) -> Dictionary:
        elements = rule_option_elements(disabling)
        elements.extend(
            (
                (
                    "id",
                    FixedValue(
                        value=rule.id,
                        title=_("Rule ID"),
                        help=_(
                            "This ID uniquely identifies this rule in Checkmk. "
                            "Use this ID when working with rules in Checkmk REST API "
                            "calls, e.g., to show, modify or delete the rule."
                        ),
                    ),
                ),
                (
                    "_name",
                    FixedValue(
                        value=rule.ruleset.name,
                        title=_("Ruleset name"),
                        help=_(
                            "This name uniquely identifies the rule set in Checkmk. "
                            "Use this name when working with rule sets and rules in "
                            "Checkmk REST API calls, e.g. to create a new rule."
                        ),
                    ),
                ),
            )
        )

        if is_locked_by_quick_setup(rule.locked_by, check_reference_exists=False):
            elements.append(
                (
                    "source",
                    FixedValue(
                        value=rule.locked_by["instance_id"],
                        title=_("Source"),
                        totext=quick_setup_render_link(rule.locked_by),
                    ),
                )
            )

        return Dictionary(
            title=_("Rule properties"),
            optional_keys=False,
            render="form",
            elements=elements,
            show_more_keys=["id", "_name"],
        )


class VSExplicitConditions(Transform):
    """Valuespec for editing a set of explicit rule conditions"""

    def __init__(self, rulespec: Rulespec, render: Literal["normal", "form_part"]) -> None:
        self._rulespec = rulespec
        super().__init__(
            valuespec=Dictionary(
                elements=self._condition_elements(),
                headers=[
                    (_("Folder"), "condition explicit", ["folder_path"]),
                    (_("Host tags"), "condition explicit", ["host_tags"]),
                    (_("Host labels"), "condition explicit", ["host_label_groups"]),
                    (_("Explicit hosts"), "condition explicit", ["explicit_hosts"]),
                    (
                        self._service_title() or _("Explicit services"),
                        "condition explicit",
                        ["explicit_services"],
                    ),
                    (_("Service labels"), "condition explicit", ["service_label_groups"]),
                ],
                optional_keys=["explicit_hosts", "explicit_services"],
                render=render,
            ),
            to_valuespec=self._to_valuespec,
            from_valuespec=self._from_valuespec,
        )

    def _condition_elements(self) -> Iterable[tuple[str, ValueSpec]]:
        elements = [
            ("folder_path", self._vs_folder()),
            ("host_tags", self._vs_host_tag_condition()),
        ]

        if allow_host_label_conditions(self._rulespec.name):
            elements.append(("host_label_groups", self._vs_host_label_condition()))

        elements.append(("explicit_hosts", self._vs_explicit_hosts()))
        elements += self._service_elements()

        return elements

    # TODO: refine type
    def _to_valuespec(self, conditions: RuleConditions) -> dict[str, Any]:
        explicit: dict[str, Any] = {
            "folder_path": conditions.host_folder,
            "host_tags": conditions.host_tags,
        }

        if allow_host_label_conditions(self._rulespec.name):
            explicit["host_label_groups"] = conditions.host_label_groups

        explicit_hosts = conditions.host_list
        if explicit_hosts is not None:
            explicit["explicit_hosts"] = explicit_hosts

        if self._rulespec.item_type:
            explicit_services = conditions.item_list
            if explicit_services is not None:
                explicit["explicit_services"] = explicit_services

            if allow_service_label_conditions(self._rulespec.name):
                explicit["service_label_groups"] = conditions.service_label_groups

        return explicit

    def _service_elements(self) -> Iterable[tuple[str, ValueSpec]]:
        if not self._rulespec.item_type:
            return []

        elements: list[tuple[str, ValueSpec]] = [
            ("explicit_services", self._vs_explicit_services())
        ]

        if allow_service_label_conditions(self._rulespec.name):
            elements.append(("service_label_groups", self._vs_service_label_condition()))

        return elements

    def _service_title(self) -> str | None:
        item_type = self._rulespec.item_type
        if not item_type:
            return None

        if item_type == "service":
            return _("Services")

        if item_type == "item":
            return self._rulespec.item_name

        raise MKUserError(None, "Invalid item type '%s'" % item_type)

    # TODO: refine type
    def _from_valuespec(self, explicit: dict[str, Any]) -> RuleConditions:
        host_label_groups = (
            explicit["host_label_groups"]
            if allow_host_label_conditions(self._rulespec.name)
            else []
        )
        service_description = None
        service_label_groups = None
        if self._rulespec.item_type:
            service_description = self._condition_list_from_valuespec(
                explicit.get("explicit_services"), is_service=True
            )
            service_label_groups = (
                explicit["service_label_groups"]
                if allow_service_label_conditions(self._rulespec.name)
                else []
            )

        return RuleConditions(
            host_folder=explicit["folder_path"],
            host_tags=explicit["host_tags"],
            host_label_groups=host_label_groups,
            host_name=self._condition_list_from_valuespec(
                explicit.get("explicit_hosts"), is_service=False
            ),
            service_description=service_description,
            service_label_groups=service_label_groups,
        )

    def _condition_list_from_valuespec(
        self, conditions: tuple[list[str], bool] | None, is_service: bool
    ) -> HostOrServiceConditions | None:
        if conditions is None:
            return None

        condition_list, negate = conditions

        sub_conditions: HostOrServiceConditionsSimple = []
        for entry in condition_list:
            if is_service:
                sub_conditions.append({"$regex": entry})
                continue

            if entry[0] == "~":
                sub_conditions.append({"$regex": entry[1:]})
                continue
            sub_conditions.append(entry)

        if not sub_conditions:
            raise MKUserError(
                None, _("Please specify at least one condition or this rule will never match.")
            )

        if negate:
            return {"$nor": sub_conditions}
        return sub_conditions

    def _vs_folder(self) -> DropdownChoice:
        return DropdownChoice(
            title=_("Folder"),
            help=_("Rule only applies to hosts directly in or below this folder."),
            choices=folder_tree().folder_choices,
            encode_value=False,
        )

    def _label_condition_help_text(self) -> HTML:
        return (
            _("Note that:")
            + html.render_ul(
                (html.render_li(_("<tt>not</tt> is the abbreviation for <tt>and not</tt>")))
                + html.render_li(
                    _(
                        "the operators are processed in the priority: <tt>not</tt>, <tt>and</tt>, "
                        "<tt>or</tt> - according to the Boolean algebra standards."
                    )
                )
            )
            + HTML.without_escaping(
                _("For more help have a look at the %s.")
                % html.render_a(
                    _("documentation"),
                    # TODO: change this doc reference from "labels#views" to "labels#conditions" once
                    #       the corresponding article is updated to the new label group conditions
                    href=doc_reference_url(DocReference.WATO_RULES_LABELS),
                    target="blank",
                )
            )
        )

    def _vs_host_label_condition(self) -> VSLabelGroups:
        return VSLabelGroups(
            show_empty_group_by_default=False,
            add_label=_("Add to condition"),
            title=_("Host labels"),
            help=_("Rule only applies to hosts matching the label conditions. ")
            + self._label_condition_help_text(),
        )

    def _vs_service_label_condition(self) -> VSLabelGroups:
        return VSLabelGroups(
            show_empty_group_by_default=False,
            add_label=_("Add to condition"),
            title=_("Service labels"),
            help=_("Use this condition to select services based on the configured service labels. ")
            + self._label_condition_help_text(),
        )

    def _vs_host_tag_condition(self) -> DictHostTagCondition:
        return DictHostTagCondition(
            title=_("Host tags"),
            help_txt=_(
                "Rule only applies to hosts that meet all of the host tag conditions listed here",
            ),
        )

    def _vs_explicit_hosts(self) -> Tuple:
        return Tuple(
            title=_("Explicit hosts"),
            elements=[
                ListOfStrings(
                    orientation="horizontal",
                    valuespec=ConfigHostname(validate=self._validate_explicit_host),  # type: ignore[arg-type]  # should be Valuespec[str]
                    help=_(
                        "Here you can enter a list of explicit host names that the rule should or should "
                        "not apply to. Leave this option disabled if you want the rule to "
                        "apply for all hosts specified by the given tags. The names that you "
                        "enter here are compared with case sensitive exact matching. Alternatively "
                        "you can use regular expressions if you enter a tilde (<tt>~</tt>) as the first "
                        "character. That regular expression must match the <i>beginning</i> of "
                        "the host names in question."
                    ),
                ),
                Checkbox(
                    label=_("<b>Negate:</b> make rule apply for <b>all but</b> the above hosts"),
                ),
            ],
        )

    def _validate_explicit_host(self, value: str, varprefix: str) -> None:
        self._validate_list_entry(value, varprefix)
        if value.startswith("~"):
            return
        try:
            HostName(value)
        except ValueError as e:
            raise MKUserError(varprefix, str(e))

    def _vs_explicit_services(self) -> Tuple:
        return Tuple(
            title=self._service_title(),
            elements=[
                self._vs_service_conditions(),
                Checkbox(
                    label=_("<b>Negate:</b> make rule apply for <b>all but</b> the above entries"),
                ),
            ],
        )

    def _explicit_service_help_text(self) -> None | str | HTML:
        itemtype = self._rulespec.item_type
        if itemtype == "service":
            return _(
                "Specify a list of service patterns this rule shall apply to. "
                "The patterns must match the <b>beginning</b> of the service "
                "in question. Adding a <tt>$</tt> to the end forces an excact "
                "match. Pattern use <b>regular expressions</b>. A <tt>.*</tt> will "
                "match an arbitrary text."
            )

        if itemtype == "item":
            if self._rulespec.item_help:
                return self._rulespec.item_help

            return _(
                "You can make the rule apply only to certain services of the "
                "specified hosts. Do this by specifying explicit <b>items</b> to "
                "match here. <b>Hint:</b> make sure to enter the item only, "
                "not the full service name. "
                "<b>Note:</b> the match is done on the <u>beginning</u> "
                "of the item in question. Regular expressions are interpreted, "
                "so appending a <tt>$</tt> will force an exact match."
            )

        return None

    def _vs_service_conditions(self) -> Transform | ListOfStrings:
        itemenum = self._rulespec.item_enum
        if itemenum:
            return Transform(
                valuespec=ListChoice(
                    choices=itemenum,
                    columns=3,
                ),
                to_valuespec=lambda item_list: [(x[:-1] if x[-1] == "$" else x) for x in item_list],
                from_valuespec=lambda item_list: [f"{x}$" for x in item_list],
            )

        return ListOfStrings(
            orientation="horizontal",
            valuespec=RegExp(size=30, mode=RegExp.prefix, validate=self._validate_list_entry),
            help=self._explicit_service_help_text(),
        )

    def _validate_list_entry(self, value: str | None, varprefix: str) -> None:
        if value and value.startswith("!"):
            raise MKUserError(varprefix, _('It\'s not allowed to use a leading "!" here.'))

    def value_to_html(self, value: RuleConditions) -> ValueSpecText:
        with output_funnel.plugged():
            html.open_ul(class_="conditions")
            renderer = RuleConditionRenderer()
            conditions = list(renderer.render(self._rulespec, value))
            if conditions:
                for condition in conditions:
                    html.li(condition, class_="condition")
            else:
                html.li(_("No conditions"), class_="no_conditions")
            html.close_ul()
            return HTML.without_escaping(output_funnel.drain())


class RuleConditionRenderer:
    def render(
        self,
        rulespec: Rulespec,
        conditions: RuleConditions,
    ) -> Iterable[HTML]:
        yield from self._tag_conditions(conditions.host_tags)
        yield from self._host_label_conditions(conditions)
        yield from self._host_conditions(conditions)
        yield from self._service_conditions(
            rulespec.item_type, rulespec.item_name, conditions.service_description
        )
        yield from self._service_label_conditions(conditions)

    def _tag_conditions(
        self, host_tag_conditions: Mapping[TagGroupID, TagCondition]
    ) -> Iterable[HTML]:
        for taggroup_id, tag_spec in host_tag_conditions.items():
            if isinstance(tag_spec, dict) and "$or" in tag_spec:
                yield HTML.without_escaping(" <i>or</i> ").join(
                    [
                        self._single_tag_condition(
                            taggroup_id,
                            sub_spec,
                        )
                        for sub_spec in cast(
                            TagConditionOR,
                            tag_spec,
                        )["$or"]
                    ]
                )
            elif isinstance(tag_spec, dict) and "$nor" in tag_spec:
                yield HTML.without_escaping(_("Neither") + " ") + HTML.without_escaping(
                    " <i>nor</i> "
                ).join(
                    [
                        self._single_tag_condition(
                            taggroup_id,
                            sub_spec,
                        )
                        for sub_spec in cast(
                            TagConditionNOR,
                            tag_spec,
                        )["$nor"]
                    ]
                )
            else:
                yield self._single_tag_condition(
                    taggroup_id,
                    cast(
                        TagID | None | TagConditionNE,
                        tag_spec,
                    ),
                )

    def _single_tag_condition(
        self,
        taggroup_id: TagGroupID,
        tag_spec: TagID | None | TagConditionNE,
    ) -> HTML:
        negate = False
        if isinstance(tag_spec, dict):
            if "$ne" in tag_spec:
                negate = True
                tag_id = tag_spec["$ne"]
            else:
                raise NotImplementedError()
        else:
            tag_id = tag_spec

        tag = active_config.tags.get_tag_or_aux_tag(taggroup_id, tag_id)
        if tag and tag.title:
            if isinstance(tag, GroupedTag):
                if negate:
                    return escape_to_html_permissive(
                        _("Host tag: %s is <b>not</b> <b>%s</b>") % (tag.group.title, tag.title)
                    )
                return escape_to_html_permissive(
                    _("Host tag: %s is <b>%s</b>") % (tag.group.title, tag.title)
                )

            if negate:
                return escape_to_html_permissive(_("Host does not have tag <b>%s</b>") % tag.title)
            return escape_to_html_permissive(_("Host has tag <b>%s</b>") % tag.title)

        if negate:
            return escape_to_html_permissive(
                _("Unknown tag: Host has <b>not</b> the tag <tt>%s</tt>") % str(tag_id)
            )

        return escape_to_html_permissive(
            _("Unknown tag: Host has the tag <tt>%s</tt>") % str(tag_id)
        )

    def _host_label_conditions(self, conditions: RuleConditions) -> Iterable[HTML]:
        return self._label_conditions(conditions.host_label_groups, "host", _("Host"))

    def _service_label_conditions(self, conditions: RuleConditions) -> Iterable[HTML]:
        return self._label_conditions(conditions.service_label_groups, "service", _("Service"))

    def _label_conditions(
        self,
        label_conditions: LabelGroups,
        object_type: Literal["service", "host"],
        object_title: str,
    ) -> Iterable[HTML]:
        if not label_conditions:
            return

        labels_html = render_label_groups(label_conditions, object_type)
        yield HTML.with_escaping(_("%s matching labels: ") % object_title) + labels_html

    def _host_conditions(self, conditions: RuleConditions) -> Iterable[HTML]:
        if conditions.host_name is None:
            return

        # Other cases should not occur, e.g. list of explicit hosts
        # plus ALL_HOSTS.
        condition_txt = self._render_host_condition_text(conditions.host_name)
        if condition_txt:
            yield condition_txt

    def _render_host_condition_text(
        self,
        conditions: HostOrServiceConditions,
    ) -> HTML:
        if conditions == []:
            return escape_to_html_permissive(
                _("This rule does <b>never</b> apply due to an empty list of explicit hosts!")
            )

        is_negate, host_name_conditions = ruleset_matcher.parse_negated_condition_list(conditions)

        condition: list[HTML] = [escape_to_html_permissive(_("Host name"))]

        regex_count = len(
            [x for x in host_name_conditions if isinstance(x, dict) and "$regex" in x]
        )

        lookup_cache = folder_lookup_cache().get_cache()
        text_list: list[HTML] = []
        if regex_count == len(host_name_conditions) or regex_count == 0:
            # Entries are either complete regex or no regex at all
            if is_negate:
                phrase = _("is not one of regex") if regex_count else _("is not one of")
            else:
                phrase = _("matches one of regex") if regex_count else _("is")
            condition.append(HTML.with_escaping(phrase))

            for host_spec in host_name_conditions:
                if isinstance(host_spec, dict) and "$regex" in host_spec:
                    text_list.append(HTMLWriter.render_b(host_spec["$regex"]))
                elif isinstance(host_spec, str):
                    # Make sure that the host exists and the lookup will not fail
                    # Otherwise the entire config would be read
                    folder_hint = lookup_cache.get(HostName(host_spec))
                    if (
                        folder_hint is not None
                        and (host := Host.host(HostName(host_spec))) is not None
                    ):
                        text_list.append(
                            HTMLWriter.render_b(HTMLWriter.render_a(host_spec, host.edit_url()))
                        )
                    else:
                        text_list.append(HTMLWriter.render_b(host_spec))
                else:
                    raise ValueError("Unsupported host spec")

        else:
            # Mixed entries
            for host_spec in host_name_conditions:
                if isinstance(host_spec, dict) and "$regex" in host_spec:
                    expression = _("does not match regex") if is_negate else _("matches regex")
                    text_list.append(
                        HTML.with_escaping(expression + " ")
                        + HTMLWriter.render_b(host_spec["$regex"])
                    )
                elif isinstance(host_spec, str):
                    expression = _("is not") if is_negate else _("is")
                    # Make sure that the host exists and the lookup will not fail
                    # Otherwise the entire config would be read
                    folder_hint = lookup_cache.get(HostName(host_spec))
                    if (
                        folder_hint is not None
                        and (host := Host.host(HostName(host_spec))) is not None
                    ):
                        text_list.append(
                            HTML.with_escaping(expression + " ")
                            + HTMLWriter.render_b(HTMLWriter.render_a(host_spec, host.edit_url()))
                        )
                    else:
                        text_list.append(
                            escape_to_html_permissive(expression + " ")
                            + HTMLWriter.render_b(host_spec)
                        )
                else:
                    raise ValueError("Unsupported host spec")

        if len(text_list) == 1:
            condition.append(text_list[0])
        else:
            condition.append(HTML.without_escaping(", ").join(text_list[:-1]))
            condition.append(HTML.with_escaping(_("or ")) + text_list[-1])

        return HTML.without_escaping(" ").join(condition)

    def _service_conditions(
        self,
        item_type: str | None,
        item_name: str | None,
        conditions: HostOrServiceConditions | None,
    ) -> Iterable[HTML]:
        if not item_type or conditions is None:
            return

        is_negate, service_conditions = ruleset_matcher.parse_negated_condition_list(conditions)
        if not service_conditions:
            yield HTML.with_escaping(_("Does not match any service"))
            return

        condition = HTML.empty()
        if item_type == "service":
            condition = HTML.with_escaping(_("Service name"))
        elif item_type == "item":
            if item_name is not None:
                condition = HTML.with_escaping(item_name)
            else:
                condition = HTML.with_escaping(_("Item"))
        condition += HTML.without_escaping(" ")

        exact_match_count = len(
            [x for x in service_conditions if not isinstance(x, dict) or x["$regex"][-1] == "$"]
        )

        text_list: list[HTML] = []
        if exact_match_count == len(service_conditions) or exact_match_count == 0:
            if is_negate:
                phrase = _("is not ") if exact_match_count else _("does not begin with ")
            else:
                phrase = _("is ") if exact_match_count else _("begins with ")
            condition += HTML.with_escaping(phrase)

            for item_spec in service_conditions:
                if isinstance(item_spec, dict) and "$regex" in item_spec:
                    text_list.append(HTMLWriter.render_b(item_spec["$regex"].rstrip("$")))
                elif isinstance(item_spec, str):
                    text_list.append(HTMLWriter.render_b(item_spec.rstrip("$")))
                else:
                    raise ValueError("Unsupported item spec")
        else:
            for item_spec in service_conditions:
                if isinstance(item_spec, dict) and "$regex" in item_spec:
                    spec = item_spec["$regex"]
                elif isinstance(item_spec, str):
                    spec = item_spec
                else:
                    raise ValueError("Unsupported item spec")

                is_exact = spec[-1] == "$"
                if is_negate:
                    expression = _("is not ") if is_exact else _("begins not with ")
                else:
                    expression = _("is ") if is_exact else _("begins with ")
                text_list.append(
                    HTML.with_escaping(expression) + HTMLWriter.render_b(spec.rstrip("$"))
                )

        if len(text_list) == 1:
            condition += text_list[0]
        else:
            condition += HTML.without_escaping(", ").join(text_list[:-1])
            condition += _(" or ") + text_list[-1]

        if condition:
            yield condition


class ModeEditRule(ABCEditRuleMode):
    @classmethod
    def name(cls) -> str:
        return "edit_rule"

    @classmethod
    def set_vars(cls, rule_spec_name: str, rule_id: str) -> None:
        request.set_var(cls.VAR_RULE_ID, rule_id)
        request.set_var(cls.VAR_RULE_SPEC_NAME, rule_spec_name)

    def _save_rule(self) -> None:
        # Just editing without moving to other folder
        self._ruleset.edit_rule(self._orig_rule, self._rule)
        self._rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )


class ModeCloneRule(ABCEditRuleMode):
    @classmethod
    def name(cls) -> str:
        return "clone_rule"

    def title(self) -> str:
        return _("Copy rule: %s") % self._rulespec.title

    def _set_rule(self) -> None:
        super()._set_rule()
        self._rule = self._orig_rule.clone(preserve_id=False)

    def _save_rule(self) -> None:
        self._ruleset.clone_rule(self._orig_rule, self._rule)
        self._rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )

    def _remove_from_orig_folder(self) -> None:
        pass  # Cloned rule is not yet in folder, don't try to remove

    def _page_form_quick_setup_warning(self) -> None:
        if is_locked_by_quick_setup(self._orig_rule.locked_by):
            quick_setup_duplication_warning(self._orig_rule.locked_by, "rule")


class ModeNewRule(ABCEditRuleMode):
    @classmethod
    def name(cls) -> str:
        return "new_rule"

    def title(self) -> str:
        return _("Add rule: %s") % self._rulespec.title

    def _set_folder(self) -> None:
        tree = folder_tree()
        if request.has_var("_new_dflt_rule"):
            # Start creating a new rule with default selections (root folder)
            self._folder = tree.root_folder()

        elif request.has_var("_new_rule"):
            # Start creating a new rule in the chosen folder
            self._folder = tree.folder(request.get_ascii_input_mandatory("rule_folder"))

        elif request.has_var("_new_host_rule"):
            # Start creating a new rule for a specific host
            self._folder = folder_from_request(
                request.var("folder"), request.get_ascii_input("host")
            )

        else:
            # Submitting the create dialog
            try:
                self._folder = tree.folder(self._get_folder_path_from_vars())
            except MKUserError:
                # Folder can not be gathered from form if an error occurs
                folder = mandatory_parameter("rule_folder", request.var("rule_folder"))
                self._folder = tree.folder(folder)

    def _get_folder_path_from_vars(self) -> str:
        return self._get_rule_conditions_from_vars().host_folder

    def _set_rule(self) -> None:
        host_name_conditions: HostOrServiceConditions | None = None
        service_description_conditions: HostOrServiceConditions | None = None

        if request.has_var("_new_host_rule"):
            hostname = request.get_ascii_input("host")
            if hostname:
                host_name_conditions = [hostname]

            if self._rulespec.item_type:
                item = (
                    mk_eval(request.get_str_input_mandatory("item"))
                    if request.has_var("item")
                    else None
                )
                if item is not None:
                    service_description_conditions = [{"$regex": "%s$" % escape_regex_chars(item)}]

        self._rule = Rule.from_ruleset_defaults(self._folder, self._ruleset)
        try:
            # If the rulespec already uses the new form spec, use the DEFAULT_VALUE sentinel
            # instead of an auto-generated valuespec:default_value()
            if _get_rule_render_mode() == RenderMode.FRONTEND:
                _tmp = self._ruleset.rulespec.form_spec
                self._rule.value = DEFAULT_VALUE
        except FormSpecNotImplementedError:
            pass
        self._rule.update_conditions(
            RuleConditions(
                host_folder=self._folder.path(),
                host_tags={},
                host_label_groups=[],
                host_name=host_name_conditions,
                service_description=service_description_conditions,
                service_label_groups=[],
            )
        )

    def _save_rule(self) -> None:
        index = self._ruleset.append_rule(self._folder, self._rule)
        self._rulesets.save_folder(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )
        self._ruleset.add_new_rule_change(index, self._folder, self._rule)

    def _success_message(self) -> str:
        return _('Created new rule in ruleset "%s" in folder "%s"') % (
            self._ruleset.title(),
            self._folder.alias_path(),
        )


class ModeExportRule(ABCEditRuleMode):
    @classmethod
    def name(cls) -> str:
        return "export_rule"

    def title(self) -> str:
        return _("Rule representation: %s") % self._rulespec.title

    def _save_rule(self) -> None:
        pass

    def page(self) -> None:
        rule_config = self._rule.ruleset.valuespec().mask(self._rule.value)
        content_id = "rule_representation"
        success_msg = _("Successfully copied to clipboard.")

        with html.form_context("rule_representation", only_close=True):
            html.p(
                _(
                    "To set the value of a rule using the REST API, you need to set the "
                    "<tt>value_raw</tt> field. The value of this fields is individual for each rule set. "
                    "To help you understand what kind of data structure you need to provide, this rule "
                    "export mechanism is showing you the value you need to set for a given rule. The "
                    "value needs to be a string representation of a compatible Python data structure."
                )
            )
            html.p(_("You can copy and use the data structure below in your REST API requests."))
            forms.header(_("Rule value representation for REST API"))
            forms.section("Rule value representation")
            html.text_area(
                content_id, deflt=repr(repr(rule_config)), id_=content_id, readonly="true"
            )
            html.icon_button(
                url=None,
                title=_("Copy rule value representation to clipboard"),
                icon="clone",
                onclick=f"cmk.utils.copy_dom_element_content_to_clipboard({json.dumps(content_id)}, {json.dumps(success_msg)})",
            )

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=list(self._page_menu_dropdowns()),
            breadcrumb=breadcrumb,
        )

    def _page_menu_dropdowns(self) -> Iterable[PageMenuDropdown]:
        if this_rule_topic := self._page_menu_topic_this_rule():
            yield PageMenuDropdown(
                name="rule",
                title=_("Rule"),
                topics=[this_rule_topic],
            )

        yield PageMenuDropdown(
            name="related",
            title=_("Related"),
            topics=[
                PageMenuTopic(
                    title=_("Setup"),
                    entries=list(self._page_menu_entries_related()),
                ),
            ],
        )


@request_memoize()
def _get_rule_render_mode() -> RenderMode:
    # Settings via url overwrite config based settings
    if (rendering_mode := html.request.var("rule_render_mode", None)) is None:
        rendering_mode = active_config.vue_experimental_features.get(
            "rule_render_mode", RenderMode.FRONTEND.value
        )

    match rendering_mode:
        case RenderMode.BACKEND.value:
            return RenderMode.BACKEND
        case RenderMode.FRONTEND.value:
            return RenderMode.FRONTEND
        case RenderMode.BACKEND_AND_FRONTEND.value:
            return RenderMode.BACKEND_AND_FRONTEND
        case _:
            raise MKGeneralException(_("Unknown rendering mode %s") % rendering_mode)


class MatchItemGeneratorUnknownRuleSets(ABCMatchItemGenerator):
    def generate_match_items(self) -> MatchItems:
        yield MatchItem(
            title=_("Unknown rulesets"),
            topic=_("Setup"),
            url=makeuri_contextless(
                request,
                [("mode", "unknown_rulesets")],
                filename="wato.py",
            ),
            match_texts=[_("Unknown rulesets")],
        )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True


class ModeUnknownRulesets(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "unknown_rulesets"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["rulesets"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        request.set_var("group", "monconf")
        return ModeRulesetGroup

    def title(self) -> str:
        return _("Unknown rulesets")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="rulesets",
                    title=_("Rulesets"),
                    topics=[
                        PageMenuTopic(
                            title=_("On selected rules"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Delete selected rules"),
                                    shortcut_title=_("Delete selected rules"),
                                    icon_name="delete",
                                    item=make_confirmed_form_submit_link(
                                        form_name="bulk_delete_selected_unknown_rulesets",
                                        button_name="_bulk_delete_selected_unknown_rulesets",
                                        title=_("Delete selected rulesets"),
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                )
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Service monitoring rules"),
                                    icon_name="rulesets",
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [
                                                ("group", "monconf"),
                                                ("mode", "rulesets"),
                                            ]
                                        )
                                    ),
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

    def _unknown_rulesets(
        self, *, debug: bool
    ) -> tuple[
        Sequence[Ruleset],
        Mapping[RulesetName, Sequence[tuple[FolderPath, RuleSpec[object]]]],
    ]:
        all_rulesets = AllRulesets.load_all_rulesets()
        rulesets = all_rulesets.get_rulesets()

        found_rule_sets: dict[RulesetName, Ruleset] = {}
        unknown_rule_sets: dict[RulesetName, list[tuple[FolderPath, RuleSpec[object]]]] = {}
        for rule_set_name in find_unknown_check_parameter_rule_sets(debug=debug).result:
            for ty in RuleGroupType:
                if (rule_set := rulesets.get(f"{ty.value}:{rule_set_name}")) is not None:
                    found_rule_sets.setdefault(rule_set.name, rule_set)

        for folder_path, rule_specs_by_name in all_rulesets.get_unknown_rulesets().items():
            for rule_set_name, rule_specs in rule_specs_by_name.items():
                if rule_set_name not in found_rule_sets:
                    unknown_rule_sets.setdefault(rule_set_name, []).extend(
                        [(folder_path, rs) for rs in rule_specs]
                    )

        return list(found_rule_sets.values()), unknown_rule_sets

    def _show_row_unknown_check_parameter_ruleset(
        self, table: Table, unknown_ruleset_name: str, rule_nr: int, rule: Rule
    ) -> None:
        table.row()

        table.cell(
            html.render_input(
                "_toggle_group",
                type_="button",
                class_="checkgroup",
                onclick="cmk.selection.toggle_group_rows(this);",
                value="X",
            ),
            sortable=False,
            css=["checkbox"],
        )
        html.checkbox("_c_unknown_cp_rule_%s" % rule.id)

        table.cell(_("Actions"), css=["buttons"])
        html.icon_button(
            make_confirm_delete_link(
                url=make_action_link(
                    [
                        ("mode", "unknown_rulesets"),
                        ("_delete_cp_ruleset_name", unknown_ruleset_name),
                        ("_delete_cp_rule_id", rule.id),
                    ]
                ),
                title=_("Delete unknown rule"),
                message=_("#%s of unknown ruleset %r") % (rule_nr, unknown_ruleset_name),
            ),
            _("Delete"),
            "delete",
        )

        table.cell("#", css=["narrow nowrap"])
        html.write_text_permissive(rule_nr)
        table.cell(_("Folder"), rule.folder.title())
        table.cell(_("ID"), rule.id)
        table.cell(_("Value"), HTMLWriter.render_tt(pformat(rule.value).replace("\n", "<br>")))
        table.cell(
            _("Conditions"),
            HTMLWriter.render_tt(
                pformat(
                    rule.get_rule_conditions().to_config(UseHostFolder.HOST_FOLDER_FOR_UI)
                ).replace("\n", "<br>")
            ),
        )

    def _show_row_unknown_rulespec(
        self,
        table: Table,
        unknown_ruleset_name: str,
        rule_nr: int,
        folder_path: str,
        rulespec: RuleSpec[object],
    ) -> None:
        table.row()

        table.cell(
            html.render_input(
                "_toggle_group",
                type_="button",
                class_="checkgroup",
                onclick="cmk.selection.toggle_group_rows(this);",
                value="X",
            ),
            sortable=False,
            css=["checkbox"],
        )
        html.checkbox("_c_unknown_rule_%s" % rulespec["id"])

        table.cell(_("Actions"), css=["buttons"])
        html.icon_button(
            make_confirm_delete_link(
                url=make_action_link(
                    [
                        ("mode", "unknown_rulesets"),
                        ("_delete_ruleset_name", unknown_ruleset_name),
                        ("_delete_rule_id", rulespec["id"]),
                    ]
                ),
                title=_("Delete unknown rule"),
                message=_("#%s of unknown ruleset %r") % (rule_nr, unknown_ruleset_name),
            ),
            _("Delete"),
            "delete",
        )

        table.cell("#", css=["narrow nowrap"])
        html.write_text_permissive(rule_nr)
        table.cell(_("Folder"), folder_path)
        table.cell(_("ID"), rulespec["id"])
        table.cell(
            _("Value"), HTMLWriter.render_tt(pformat(rulespec["value"]).replace("\n", "<br>"))
        )
        table.cell(
            _("Conditions"),
            HTMLWriter.render_tt(pformat(rulespec["condition"]).replace("\n", "<br>")),
        )

    def page(self) -> None:
        unknown_check_parameter_rulesets, unknown_rulesets = self._unknown_rulesets(
            debug=active_config.debug
        )
        with html.form_context("bulk_delete_selected_unknown_rulesets", method="POST"):
            html.hidden_field("mode", "unknown_rulesets", add_var=True)
            with table_element(
                self.name(),
                title=None,
                searchable=False,
                sortable=False,
                foldable=Foldable.FOLDABLE_SAVE_STATE,
                limit=None,
            ) as table:
                for unknown_check_parameter_ruleset in unknown_check_parameter_rulesets:
                    table.groupheader(
                        _("Unknown ruleset: %s") % unknown_check_parameter_ruleset.name
                    )
                    for rules in unknown_check_parameter_ruleset.rules.values():
                        for rule_nr, rule in enumerate(rules):
                            self._show_row_unknown_check_parameter_ruleset(
                                table, unknown_check_parameter_ruleset.name, rule_nr, rule
                            )
                for unknown_ruleset_name, rulespecs in unknown_rulesets.items():
                    table.groupheader(_("Unknown ruleset: %s") % unknown_ruleset_name)
                    for rule_nr, (folder_path, rulespec) in enumerate(rulespecs):
                        self._show_row_unknown_rulespec(
                            table, unknown_ruleset_name, rule_nr, folder_path, rulespec
                        )

    def _delete_cp_rule(self, rulesets: AllRulesets, ruleset: Ruleset, rule: Rule) -> None:
        if is_locked_by_quick_setup(rule.locked_by):
            raise MKUserError(None, _("Cannot delete rules that are managed by Quick setup."))
        ruleset.delete_rule(rule)

    def _bulk_delete_selected_rules(
        self, selected_cp_rule_ids: Sequence[str], selected_rule_ids: Sequence[str]
    ) -> ActionResult:
        rulesets = AllRulesets.load_all_rulesets()
        do_reset = False

        by_folder: dict[Folder, list[tuple[Ruleset, Rule]]] = {}
        for ruleset in rulesets.get_rulesets().values():
            for rules in ruleset.rules.values():
                for rule in rules:
                    if rule.id in selected_cp_rule_ids:
                        by_folder.setdefault(rule.folder, []).append((ruleset, rule))
                        do_reset = True

        for folder, rulesets_and_rules in by_folder.items():
            for ruleset, rule in rulesets_and_rules:
                self._delete_cp_rule(rulesets, ruleset, rule)
            rulesets.save_folder(
                folder, pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )

        do_save = False
        for folder_path, rulespecs_by_name in rulesets.get_unknown_rulesets().items():
            for ruleset_name, rulespecs in rulespecs_by_name.items():
                for rulespec in rulespecs:
                    if rulespec["id"] in selected_rule_ids:
                        rulesets.delete_unknown_rule(folder_path, ruleset_name, rulespec["id"])
                        do_save = True
                        do_reset = True

        if do_save:
            rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)
        if do_reset:
            deprecations.reset_scheduling()
        return redirect(self.mode_url())

    def _delete_selected_cp_rule(
        self, selected_ruleset_name: str, selected_rule_id: str
    ) -> ActionResult:
        rulesets = AllRulesets.load_all_rulesets()
        if not (ruleset := rulesets.get_rulesets().get(selected_ruleset_name)):
            return None

        for rules in ruleset.rules.values():
            for rule in rules:
                if rule.id == selected_rule_id:
                    self._delete_cp_rule(rulesets, ruleset, rule)
                    rulesets.save_folder(
                        rule.folder,
                        pprint_value=active_config.wato_pprint_config,
                        debug=active_config.debug,
                    )
                    deprecations.reset_scheduling()
                    return redirect(self.mode_url())

        return None

    def _delete_selected_rule(
        self, selected_ruleset_name: str, selected_rule_id: str
    ) -> ActionResult:
        rulesets = AllRulesets.load_all_rulesets()
        for folder_path, rulespecs_by_name in rulesets.get_unknown_rulesets().items():
            for ruleset_name, rulespecs in rulespecs_by_name.items():
                for rulespec in rulespecs:
                    if rulespec["id"] == selected_rule_id:
                        rulesets.delete_unknown_rule(folder_path, ruleset_name, rulespec["id"])
                        rulesets.save(
                            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
                        )
                        deprecations.reset_scheduling()
                        return redirect(self.mode_url())

        return None

    def action(self) -> ActionResult:
        check_csrf_token()

        d_cp_rule_ids = [
            vn.split("_c_unknown_cp_rule_")[-1]
            for vn, _vv in request.itervars(prefix="_c_unknown_cp_rule")
        ]
        d_rule_ids = [
            vn.split("_c_unknown_rule_")[-1]
            for vn, _vv in request.itervars(prefix="_c_unknown_rule")
        ]
        if request.var("_bulk_delete_selected_unknown_rulesets") and (d_cp_rule_ids or d_rule_ids):
            return self._bulk_delete_selected_rules(d_cp_rule_ids, d_rule_ids)

        if (d_ruleset_name := request.var("_delete_cp_ruleset_name")) and (
            d_rule_id := request.var("_delete_cp_rule_id")
        ):
            return self._delete_selected_cp_rule(d_ruleset_name, d_rule_id)

        if (d_ruleset_name := request.var("_delete_ruleset_name")) and (
            d_rule_id := request.var("_delete_rule_id")
        ):
            return self._delete_selected_rule(d_ruleset_name, d_rule_id)

        return None
