#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for trying out the logwatch patterns"""

import re
from collections.abc import Collection, Iterable, Mapping, Sequence

from livestatus import SiteConfiguration

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.checkengine.plugins import CheckPluginName

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.table import Foldable, table_element
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.wato.pages.rulesets import ModeEditRuleset
from cmk.gui.watolib.automations import (
    LocalAutomationConfig,
    make_automation_config,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.check_mk_automations import (
    analyse_service,
    analyze_service_rule_matches,
    get_service_name,
)
from cmk.gui.watolib.config_hostname import ConfigHostname
from cmk.gui.watolib.hosts_and_folders import folder_from_request, folder_preserving_link
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.rulesets import Rule, rules_grouped_by_folder, SingleRulesetRecursively
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.watolib.utils import mk_repr


def register(
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    mode_registry.register(ModePatternEditor)
    match_item_generator_registry.register(
        MatchItemGeneratorLogfilePatternAnalyzer("logfile_pattern_analyzer")
    )


class ModePatternEditor(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "pattern_editor"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["pattern_editor"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditRuleset

    def breadcrumb(self) -> Breadcrumb:
        # The ModeEditRuleset.breadcrumb_item does not know anything about the fact that this mode
        # is a child of the logwatch_rules ruleset. It can not construct the correct link to the
        # logwatch_rules ruleset in the breadcrumb. We hand over the ruleset variable name that we
        # are interested in to the mode. It's a bit hacky to do it this way, but it's currently the
        # only way to get these information to the modes breadcrumb method.
        with request.stashed_vars():
            request.set_var("varname", "logwatch_rules")
            request.del_var("host")
            request.del_var("service")
            return super().breadcrumb()

    def _from_vars(self) -> None:
        try:
            self._hostname = HostName(self._vs_host().from_html_vars("host"))
        except ValueError as e:
            raise MKUserError("host", str(e))
        self._vs_host().validate_value(self._hostname, "host")

        # TODO: validate all fields
        self._item = request.get_str_input_mandatory("file", "")
        self._match_txt = request.get_str_input_mandatory("match", "")

        self._host = folder_from_request(request.var("folder"), self._hostname).host(self._hostname)

        if self._hostname and not self._host:
            raise MKUserError(None, _("This host does not exist."))

        if self._item and not self._hostname:
            raise MKUserError(None, _("You need to specify a host name to test file matching."))

    @staticmethod
    def title_pattern_analyzer() -> str:
        return _("Log file pattern analyzer")

    def title(self) -> str:
        if not self._hostname and not self._item:
            return self.title_pattern_analyzer()
        if not self._hostname:
            return _("Log file patterns of log file %s on all hosts") % (self._item)
        if not self._item:
            return _("Log file patterns of host %s") % (self._hostname)
        return _("Log file patterns of log file %s on host %s") % (self._item, self._hostname)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Monitoring"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        return menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        if not self._host:
            return

        yield PageMenuEntry(
            title=_("Host log files"),
            icon_name="logwatch",
            item=make_simple_link(
                makeuri_contextless(request, [("host", self._hostname)], filename="logwatch.py")
            ),
        )

        if self._item:
            yield PageMenuEntry(
                title=("Show log file"),
                icon_name="logwatch",
                item=make_simple_link(
                    makeuri_contextless(
                        request,
                        [("host", self._hostname), ("file", self._item)],
                        filename="logwatch.py",
                    )
                ),
            )

    def page(self) -> None:
        html.help(
            _(
                "On this page you can test the defined log file patterns against a custom text, "
                "for example a line from a log file. Using this dialog it is possible to analyze "
                "and debug your whole set of log file patterns."
            )
        )

        self._show_try_form()
        self._show_patterns(site_configs=active_config.sites, debug=active_config.debug)

    def _show_try_form(self) -> None:
        with html.form_context("try"):
            forms.header(_("Try pattern match"))
            forms.section(_("Host name"))
            self._vs_host().render_input("host", self._hostname)
            forms.section(_("Log file"))
            html.help(_("Here you need to insert the original file or pathname"))
            html.text_input("file", size=80)
            forms.section(_("Text to match"))
            html.help(
                _(
                    "You can insert some text (e.g. a line of the logfile) to test the patterns defined "
                    "for this logfile. All patterns for this logfile are listed below. Matching patterns "
                    'will be highlighted after clicking the "Try out" button.'
                )
            )
            html.text_input("match", cssclass="match", size=100)
            forms.end()
            html.button("_try", _("Try out"))
            request.del_var("folder")  # Never hand over the folder here
            html.hidden_fields()

    def _vs_host(self) -> ConfigHostname:
        return ConfigHostname()

    def _show_patterns(
        self, *, site_configs: Mapping[SiteId, SiteConfiguration], debug: bool
    ) -> None:
        from cmk.gui import logwatch

        ruleset = SingleRulesetRecursively.load_single_ruleset_recursively("logwatch_rules").get(
            "logwatch_rules"
        )

        html.h3(_("Log file patterns"))
        if ruleset.is_empty():
            html.open_div(class_="info")
            html.write_text_permissive(
                "There are no logfile patterns defined. You may create "
                'logfile patterns using the <a href="%s">Rule Editor</a>.'
                % folder_preserving_link(
                    [
                        ("mode", "edit_ruleset"),
                        ("varname", "logwatch_rules"),
                    ]
                )
            )
            html.close_div()

        # Loop all rules for this ruleset
        already_matched = False
        abs_rulenr = 0
        folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))

        rules = ruleset.get_rules()
        rule_match_results = (
            self._analyze_rule_matches(
                make_automation_config(site_configs[self._host.site_id()]),
                self._hostname,
                self._item,
                [r[2] for r in rules],
                debug=debug,
            )
            if self._hostname and self._host
            else {}
        )

        for folder, folder_rules in rules_grouped_by_folder(rules, folder):
            with table_element(
                f"logfile_patterns_{folder.ident()}",
                title="%s %s (%d)"
                % (
                    _("Rules in folder"),
                    folder.alias_path(),
                    ruleset.num_rules_in_folder(folder),
                ),
                css="logwatch",
                searchable=False,
                sortable=False,
                limit=None,
                foldable=Foldable.FOLDABLE_SAVE_STATE,
                omit_update_header=True,
            ) as table:
                for _folder, rulenr, rule in folder_rules:
                    # If no host/file given match all rules
                    rule_matches = rule_match_results[rule.id] if rule_match_results else False

                    abs_rulenr += 1

                    # TODO: What's this?
                    pattern_list = rule.value
                    if isinstance(pattern_list, dict):
                        pattern_list = pattern_list["reclassify_patterns"]

                    # Each rule can hold no, one or several patterns. Loop them all here
                    for state, pattern, comment in pattern_list:
                        match_class = ""
                        disp_match_txt = HTML.empty()
                        match_img = ""
                        if rule_matches:
                            # Applies to the given host/service
                            matched = re.search(pattern, self._match_txt)
                            if matched:
                                # Prepare highlighted search txt
                                match_start = matched.start()
                                match_end = matched.end()
                                disp_match_txt = (
                                    HTML.with_escaping(self._match_txt[:match_start])
                                    + HTMLWriter.render_span(
                                        self._match_txt[match_start:match_end], class_="match"
                                    )
                                    + HTML.with_escaping(self._match_txt[match_end:])
                                )

                                if not already_matched:
                                    # First match
                                    match_class = "match first"
                                    match_img = "checkmark"
                                    match_title = _(
                                        "This log file pattern matches first and will be used for "
                                        "defining the state of the given line."
                                    )
                                    already_matched = True
                                else:
                                    # subsequent match
                                    match_class = "match"
                                    match_img = "checkmark_orange"
                                    match_title = _(
                                        "This log file pattern matches but another matched first."
                                    )
                            else:
                                match_img = "hyphen"
                                match_title = _(
                                    "This log file pattern does not match the given string."
                                )
                        else:
                            # rule does not match
                            match_img = "hyphen"
                            match_title = _("The rule conditions do not match.")

                        table.row()
                        table.cell("#", css=["narrow nowrap"])
                        html.write_text_permissive(rulenr)
                        table.cell(_("Match"))
                        html.icon(match_img, match_title)

                        cls = (
                            ["state%d" % logwatch.level_state(state), "fillbackground"]
                            if match_class == "match first"
                            else []
                        )

                        table.cell(
                            _("Checkmk state"),
                            HTMLWriter.render_span(logwatch.level_name(state)),
                            css=cls,
                        )
                        table.cell(
                            _("Logwatch state"),
                            HTMLWriter.render_span(logwatch.logwatch_level_name(state)),
                            css=cls,
                        )
                        table.cell(_("Pattern"), HTMLWriter.render_tt(pattern))
                        table.cell(_("Comment"), comment)
                        table.cell(_("Matched line"), disp_match_txt)

                    table.row(fixed=True, collect_headers=False)
                    table.cell(colspan=7)
                    edit_url = folder_preserving_link(
                        [
                            ("mode", "edit_rule"),
                            ("varname", "logwatch_rules"),
                            ("rulenr", rulenr),
                            ("item", mk_repr(self._item).decode()),
                            ("rule_folder", folder.path()),
                            ("rule_id", rule.id),
                        ]
                    )
                    html.icon_button(edit_url, _("Edit this rule"), "edit")

    def _analyze_rule_matches(
        self,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        host_name: HostName,
        item: str,
        rules: Sequence[Rule],
        *,
        debug: bool,
    ) -> dict[str, bool]:
        service_desc = get_service_name(
            host_name, CheckPluginName("logwatch"), item, debug=debug
        ).service_name
        service_labels = analyse_service(
            automation_config,
            host_name,
            service_desc,
            debug=debug,
        ).labels

        return {
            rule_id: bool(matches)
            for rule_id, matches in analyze_service_rule_matches(
                host_name,
                item,
                service_labels,
                [r.to_single_base_ruleset() for r in rules],
                debug=debug,
            ).results.items()
            for rule in rules
        }


class MatchItemGeneratorLogfilePatternAnalyzer(ABCMatchItemGenerator):
    def generate_match_items(self) -> MatchItems:
        title = ModePatternEditor.title_pattern_analyzer()
        yield MatchItem(
            title=title,
            topic=_("Miscellaneous"),
            url=makeuri_contextless(
                request,
                [("mode", ModePatternEditor.name())],
                filename="wato.py",
            ),
            match_texts=[title],
        )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True
