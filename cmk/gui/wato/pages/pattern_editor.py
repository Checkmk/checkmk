#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for trying out the logwatch patterns"""

from typing import Optional, Type, Iterable
import re
from six import ensure_str

from cmk.utils.type_defs import CheckPluginNameStr, HostName, ServiceName, Item

import cmk.gui.watolib as watolib
from cmk.gui.table import table_element
import cmk.gui.forms as forms
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.wato.pages.rulesets import ModeEditRuleset
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
)
from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    ConfigHostname,
)

# Tolerate this for 1.6. Should be cleaned up in future versions,
# e.g. by trying to move the common code to a common place
import cmk.base.export


@mode_registry.register
class ModePatternEditor(WatoMode):
    @classmethod
    def name(cls):
        return "pattern_editor"

    @classmethod
    def permissions(cls):
        return ["pattern_editor"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditRuleset

    def breadcrumb(self) -> Breadcrumb:
        # The ModeEditRuleset.breadcrumb_item does not know anything about the fact that this mode
        # is a child of the logwatch_rules ruleset. It can not construct the correct link to the
        # logwatch_rules ruleset in the breadcrumb. We hand over the ruleset variable name that we
        # are interested in to the mode. It's a bit hacky to do it this way, but it's currently the
        # only way to get these information to the modes breadcrumb method.
        with html.stashed_vars():
            html.request.set_var("varname", "logwatch_rules")
            return super().breadcrumb()

    def _from_vars(self):
        self._hostname = self._vs_host().from_html_vars("host")
        self._vs_host().validate_value(self._hostname, "host")

        # TODO: validate all fields
        self._item = html.request.get_unicode_input_mandatory('file', u'')
        self._match_txt = html.request.get_unicode_input_mandatory('match', u'')

        self._host = watolib.Folder.current().host(self._hostname)

        if self._hostname and not self._host:
            raise MKUserError(None, _("This host does not exist."))

        if self._item and not self._hostname:
            raise MKUserError(None, _("You need to specify a host name to test file matching."))

    def title(self):
        if not self._hostname and not self._item:
            return _("Logfile pattern analyzer")
        if not self._hostname:
            return _("Logfile patterns of logfile %s on all hosts") % (self._item)
        if not self._item:
            return _("Logfile patterns of Host %s") % (self._hostname)
        return _("Logfile patterns of logfile %s on host %s") % (self._item, self._hostname)

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
                html.makeuri_contextless([("host", self._hostname)], filename="logwatch.py")),
        )

        if self._item:
            yield PageMenuEntry(
                title=("Show log file"),
                icon_name="logwatch",
                item=make_simple_link(
                    html.makeuri_contextless([("host", self._hostname), ("file", self._item)],
                                             filename="logwatch.py")),
            )

    def page(self):
        html.help(
            _('On this page you can test the defined logfile patterns against a custom text, '
              'for example a line from a logfile. Using this dialog it is possible to analyze '
              'and debug your whole set of logfile patterns.'))

        self._show_try_form()
        self._show_patterns()

    def _show_try_form(self):
        html.begin_form('try')
        forms.header(_('Try Pattern Match'))
        forms.section(_('Hostname'))
        self._vs_host().render_input("host", self._hostname)
        forms.section(_('Logfile'))
        html.text_input('file')
        forms.section(_('Text to match'))
        html.help(
            _('You can insert some text (e.g. a line of the logfile) to test the patterns defined '
              'for this logfile. All patterns for this logfile are listed below. Matching patterns '
              'will be highlighted after clicking the "Try out" button.'))
        html.text_input('match', cssclass='match', size=100)
        forms.end()
        html.button('_try', _('Try out'))
        html.request.del_var('folder')  # Never hand over the folder here
        html.hidden_fields()
        html.end_form()

    def _vs_host(self):
        return ConfigHostname()

    def _show_patterns(self):
        import cmk.gui.logwatch as logwatch
        collection = watolib.SingleRulesetRecursively("logwatch_rules")
        collection.load()
        ruleset = collection.get("logwatch_rules")

        html.h3(_('Logfile patterns'))
        if ruleset.is_empty():
            html.open_div(class_="info")
            html.write_text('There are no logfile patterns defined. You may create '
                            'logfile patterns using the <a href="%s">Rule Editor</a>.' %
                            watolib.folder_preserving_link([
                                ('mode', 'edit_ruleset'),
                                ('varname', 'logwatch_rules'),
                            ]))
            html.close_div()

        # Loop all rules for this ruleset
        already_matched = False
        abs_rulenr = 0
        for folder, rulenr, rule in ruleset.get_rules():
            # Check if this rule applies to the given host/service
            if self._hostname:
                service_desc = self._get_service_description(self._hostname, "logwatch", self._item)

                # If hostname (and maybe filename) try match it
                rule_matches = rule.matches_host_and_item(watolib.Folder.current(), self._hostname,
                                                          self._item, service_desc)
            else:
                # If no host/file given match all rules
                rule_matches = True

            html.begin_foldable_container("rule",
                                          "%s" % abs_rulenr,
                                          True,
                                          HTML("<b>Rule #%d</b>" % (abs_rulenr + 1)),
                                          indent=False)
            with table_element("pattern_editor_rule_%d" % abs_rulenr, sortable=False) as table:
                abs_rulenr += 1

                # TODO: What's this?
                pattern_list = rule.value
                if isinstance(pattern_list, dict):
                    pattern_list = pattern_list["reclassify_patterns"]

                # Each rule can hold no, one or several patterns. Loop them all here
                for state, pattern, comment in pattern_list:
                    match_class = ''
                    disp_match_txt = HTML('')
                    match_img = ''
                    if rule_matches:
                        # Applies to the given host/service
                        reason_class = 'reason'

                        matched = re.search(pattern, self._match_txt)
                        if matched:

                            # Prepare highlighted search txt
                            match_start = matched.start()
                            match_end = matched.end()
                            disp_match_txt = html.render_text(self._match_txt[:match_start]) \
                                             + html.render_span(self._match_txt[match_start:match_end], class_="match")\
                                             + html.render_text(self._match_txt[match_end:])

                            if not already_matched:
                                # First match
                                match_class = 'match first'
                                match_img = 'match'
                                match_title = _(
                                    'This logfile pattern matches first and will be used for '
                                    'defining the state of the given line.')
                                already_matched = True
                            else:
                                # subsequent match
                                match_class = 'match'
                                match_img = 'imatch'
                                match_title = _(
                                    'This logfile pattern matches but another matched first.')
                        else:
                            match_img = 'nmatch'
                            match_title = _('This logfile pattern does not match the given string.')
                    else:
                        # rule does not match
                        reason_class = 'noreason'
                        match_img = 'nmatch'
                        match_title = _('The rule conditions do not match.')

                    table.row(css=reason_class)
                    table.cell(_('Match'))
                    html.icon("rule%s" % match_img, match_title)

                    cls = ''
                    if match_class == 'match first':
                        cls = 'svcstate state%d' % logwatch.level_state(state)
                    table.cell(_('State'), logwatch.level_name(state), css=cls)
                    table.cell(_('Pattern'), html.render_tt(pattern))
                    table.cell(_('Comment'), html.render_text(comment))
                    table.cell(_('Matched line'), disp_match_txt)

                table.row(fixed=True)
                table.cell(colspan=5)
                edit_url = watolib.folder_preserving_link([
                    ("mode", "edit_rule"),
                    ("varname", "logwatch_rules"),
                    ("rulenr", rulenr),
                    ("host", self._hostname),
                    ("item", ensure_str(watolib.mk_repr(self._item))),
                    ("rule_folder", folder.path()),
                ])
                html.icon_button(edit_url, _("Edit this rule"), "edit")

            html.end_foldable_container()

    def _get_service_description(self, hostname: HostName, check_plugin_name: CheckPluginNameStr,
                                 item: Item) -> ServiceName:
        return cmk.base.export.service_description(hostname, check_plugin_name, item)
