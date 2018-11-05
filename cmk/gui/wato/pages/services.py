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
"""Modes for services and discovery"""

import json
import traceback
from hashlib import sha256

import cmk
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.table as table
import cmk.gui.weblib as weblib

from cmk.gui.plugins.wato.utils import mode_registry, may_edit_ruleset
from cmk.gui.plugins.wato.utils.base_modes import WatoMode, WatoWebApiMode
from cmk.gui.plugins.wato.utils.context_buttons import host_status_button, global_buttons

from cmk.gui.pages import register_page_handler
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.log import logger
from cmk.defines import short_service_state_name


@mode_registry.register
class ModeDiscovery(WatoMode):
    #TODO In the future cleanup check_source (passive/active/custom/legacy) and
    # check_state:
    # - passive: new/vanished/old/ignored/removed
    # - active/custom/legacy: old/ignored
    SERVICE_UNDECIDED = "new"
    SERVICE_VANISHED = "vanished"
    SERVICE_MONITORED = "old"
    SERVICE_IGNORED = "ignored"
    SERVICE_REMOVED = "removed"

    SERVICE_MANUAL = "manual"
    SERVICE_ACTIVE = "active"
    SERVICE_CUSTOM = "custom"
    SERVICE_LEGACY = "legacy"
    SERVICE_CLUSTERED_OLD = "clustered_old"
    SERVICE_CLUSTERED_NEW = "clustered_new"
    SERVICE_ACTIVE_IGNORED = "active_ignored"
    SERVICE_CUSTOM_IGNORED = "custom_ignored"
    SERVICE_LEGACY_IGNORED = "legacy_ignored"

    @classmethod
    def name(cls):
        return "inventory"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def _from_vars(self):
        self._host_name = html.var("host")
        self._host = watolib.Folder.current().host(self._host_name)
        if not self._host:
            raise MKGeneralException(_("You called this page with an invalid host name."))

        self._host.need_permission("read")
        self._do_scan = html.has_var("_scan")
        self._already_scanned = False
        if config.user.may("wato.services"):
            if html.has_var("_show_checkboxes"):
                config.user.save_file("discovery_checkboxes", html.var("_show_checkboxes") == "1")
            cache_options = ["@scan"] if self._do_scan else ["@noscan"]
            self._show_checkboxes = config.user.load_file("discovery_checkboxes", False)
        else:
            cache_options = ["@noscan"]
            self._show_checkboxes = False

        if html.has_var("_hide_parameters"):
            config.user.save_file("parameter_column", html.var("_hide_parameters") == "no")

        # Read current check configuration
        if html.var("ignoreerrors"):
            error_options = []
        else:
            error_options = ["@raiseerrors"]
        self._options = cache_options + error_options + [self._host_name]
        self._fixall = html.var("_fixall")

    def title(self):
        title = _("Services of host %s") % self._host_name
        if self._do_scan:
            title += _(" (live scan)")
        else:
            title += _(" (might be cached data)")
        return title

    def buttons(self):
        global_buttons()
        html.context_button(_("Folder"),
             watolib.folder_preserving_link([("mode", "folder")]), "back")

        host_status_button(self._host_name, "host")

        html.context_button(_("Properties"), watolib.folder_preserving_link([
                                                ("mode", "edit_host"),
                                                ("host", self._host_name)]), "edit")

        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"), watolib.folder_preserving_link([
                                                    ("mode", "object_parameters"),
                                                    ("host", self._host_name)]), "rulesets")
            if self._host.is_cluster():
                html.context_button(_("Clustered services"),
                     watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                             ("varname", "clustered_services")]), "rulesets")

        if not self._host.is_cluster():
            # only display for non cluster hosts
            html.context_button(_("Diagnostic"),
                 watolib.folder_preserving_link([("mode", "diag_host"),
                                         ("host", self._host_name)]), "diagnose")

    def action(self):
        if not html.check_transaction():
            return
        host = self._host
        hostname = self._host.name()
        config.user.need_permission("wato.services")
        if html.var("_refresh"):
            self._automatic_refresh_discovery(hostname)
        else:
            self._do_discovery(host)
        if not host.locked():
            self._host.clear_discovery_failed()

    def _automatic_refresh_discovery(self, hostname):
        config.user.need_permission("wato.service_discovery_to_undecided")
        config.user.need_permission("wato.service_discovery_to_monitored")
        config.user.need_permission("wato.service_discovery_to_ignored")
        config.user.need_permission("wato.service_discovery_to_removed")

        counts, _failed_hosts = watolib.check_mk_automation(self._host.site_id(), "inventory",
                                                            ["@scan", "refresh", hostname])
        count_added, _count_removed, _count_kept, _count_new = counts[hostname]
        message = _("Refreshed check configuration of host '%s' with %d services") % \
                    (hostname, count_added)
        watolib.add_service_change(self._host, "refresh-autochecks", message)
        return message

    def _do_discovery(self, host):
        check_table = self._get_check_table()
        services_to_save, remove_disabled_rule, add_disabled_rule = {}, [], []
        apply_changes = False
        for table_source, check_type, _checkgroup, item, paramstring, _params, \
            descr, _state, _output, _perfdata in check_table:

            table_target = self._get_table_target(table_source, check_type, item)

            if table_source != table_target:
                if table_target == self.SERVICE_UNDECIDED:
                    config.user.need_permission("wato.service_discovery_to_undecided")
                elif table_target in [
                        self.SERVICE_MONITORED,
                        self.SERVICE_CLUSTERED_NEW,
                        self.SERVICE_CLUSTERED_OLD,
                ]:
                    config.user.need_permission("wato.service_discovery_to_undecided")
                elif table_target == self.SERVICE_IGNORED:
                    config.user.need_permission("wato.service_discovery_to_ignored")
                elif table_target == self.SERVICE_REMOVED:
                    config.user.need_permission("wato.service_discovery_to_removed")

                if not apply_changes:
                    apply_changes = True

            if table_source == self.SERVICE_UNDECIDED:
                if table_target == self.SERVICE_MONITORED:
                    services_to_save[(check_type, item)] = paramstring
                elif table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source == self.SERVICE_VANISHED:
                if table_target != self.SERVICE_REMOVED:
                    services_to_save[(check_type, item)] = paramstring
                if table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source == self.SERVICE_MONITORED:
                if table_target in [
                        self.SERVICE_MONITORED,
                        self.SERVICE_IGNORED,
                ]:
                    services_to_save[(check_type, item)] = paramstring
                if table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source == self.SERVICE_IGNORED:
                if table_target in [
                        self.SERVICE_MONITORED,
                        self.SERVICE_UNDECIDED,
                        self.SERVICE_VANISHED,
                ]:
                    remove_disabled_rule.append(descr)
                if table_target in [
                        self.SERVICE_MONITORED,
                        self.SERVICE_IGNORED,
                ]:
                    services_to_save[(check_type, item)] = paramstring
                if table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source in [
                    self.SERVICE_CLUSTERED_NEW,
                    self.SERVICE_CLUSTERED_OLD,
            ]:
                services_to_save[(check_type, item)] = paramstring

        if apply_changes:
            need_sync = False
            if remove_disabled_rule or add_disabled_rule:
                self._save_host_service_enable_disable_rules(remove_disabled_rule,
                                                             add_disabled_rule)
                need_sync = True
            self._save_services(services_to_save, need_sync)

    def page(self):
        try:
            check_table = self._get_check_table()
        except Exception, e:
            logger.exception()
            if config.debug:
                raise
            retry_link = html.render_a(
                content=_("Retry discovery while ignoring this error (Result might be incomplete)."),
                href=html.makeuri([("ignoreerrors", "1"), ("_scan", "")])
            )
            html.show_warning("<b>%s</b>: %s<br><br>%s" %
                              (_("Service discovery failed for this host"), e, retry_link))
            return

        if not check_table and self._host.is_cluster():
            url = watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                                  ("varname", "clustered_services")])
            html.show_info(_("Could not find any service for your cluster. You first need to "
                             "specify which services of your nodes shal be added to the "
                             "cluster. This is done using the <a href=\"%s\">%s</a> ruleset.") %
                                (url, _("Clustered services")))
            return

        map_icons = {
            self.SERVICE_UNDECIDED: "undecided",
            self.SERVICE_MONITORED: "monitored",
            self.SERVICE_IGNORED: "disabled"
        }

        html.begin_form("checks_action", method="POST")
        self._show_action_buttons(check_table)
        html.hidden_fields()
        html.end_form()

        by_group = {}
        for entry in check_table:
            by_group.setdefault(entry[0], [])
            by_group[entry[0]].append(entry)

        for table_group, show_bulk_actions, header, help_text in self._ordered_table_groups():
            checks = by_group.get(table_group, [])
            if not checks:
                continue

            html.begin_form("checks_%s" % table_group, method="POST")
            table.begin(css="data", searchable=False, limit=None, sortable=False)
            if table_group in map_icons:
                group_header = "%s %s" % (html.render_icon("%s_service" % map_icons[table_group]),
                                          header)
            else:
                group_header = header
            table.groupheader(group_header + html.render_help(help_text))

            if show_bulk_actions and len(checks) > 10:
                self._bulk_actions(table_group, collect_headers=False)

            for check in sorted(checks, key=lambda c: c[6].lower()):
                self._check_row(check, show_bulk_actions)

            if show_bulk_actions:
                self._bulk_actions(table_group, collect_headers="finished")

            table.end()
            html.hidden_fields()
            html.end_form()

    #   .--action helper-------------------------------------------------------.

    def _save_services(self, checks, need_sync):
        host = self._host
        hostname = host.name()
        message = _("Saved check configuration of host '%s' with %d services") % \
                    (hostname, len(checks))
        watolib.add_service_change(host, "set-autochecks", message, need_sync=need_sync)
        watolib.check_mk_automation(host.site_id(), "set-autochecks", [hostname], checks)

    def _save_host_service_enable_disable_rules(self, to_enable, to_disable):
        self._save_service_enable_disable_rules(to_enable, value=False)
        self._save_service_enable_disable_rules(to_disable, value=True)

    # Load all disabled services rules from the folder, then check whether or not there is a
    # rule for that host and check whether or not it currently disabled the services in question.
    # if so, remove them and save the rule again.
    # Then check whether or not the services are still disabled (by other rules). If so, search
    # for an existing host dedicated negative rule that enables services. Modify this or create
    # a new rule to override the disabling of other rules.
    #
    # Do the same vice versa for disabling services.
    def _save_service_enable_disable_rules(self, services, value):
        if not services:
            return

        def _compile_patterns(services):
            return ["%s$" % s.replace("\\", "\\\\") for s in services]

        rulesets = watolib.AllRulesets()
        rulesets.load()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = watolib.Ruleset("ignored_services")

        modified_folders = []

        service_patterns = _compile_patterns(services)
        modified_folders += self._remove_from_rule_of_host(
            ruleset, service_patterns, value=not value)

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        for service in services[:]:
            value_without_host_rule = ruleset.analyse_ruleset(self._host.name(), service)[0]
            if (value == False and value_without_host_rule in [None, False]) \
               or value == value_without_host_rule:
                services.remove(service)

        service_patterns = _compile_patterns(services)
        modified_folders += self._update_rule_of_host(ruleset, service_patterns, value=value)

        for folder in modified_folders:
            rulesets.save_folder(folder)

    def _remove_from_rule_of_host(self, ruleset, service_patterns, value):
        other_rule = self._get_rule_of_host(ruleset, value)
        if other_rule:
            disable_patterns = set(other_rule.item_list).difference(service_patterns)
            other_rule.item_list = sorted(list(disable_patterns))

            if not other_rule.item_list:
                ruleset.delete_rule(other_rule)

            return [other_rule.folder]

        return []

    def _update_rule_of_host(self, ruleset, service_patterns, value):
        folder = self._host.folder()
        rule = self._get_rule_of_host(ruleset, value)

        if rule:
            rule.item_list = sorted(list(set(service_patterns).union(rule.item_list)))
            if not rule.item_list:
                ruleset.delete_rule(rule)

        elif service_patterns:
            rule = watolib.Rule.create(folder, ruleset, [self._host.name()],
                                       sorted(service_patterns))
            rule.value = value
            ruleset.prepend_rule(folder, rule)

        if rule:
            return [rule.folder]
        return []

    def _get_rule_of_host(self, ruleset, value):
        for _folder, _index, rule in ruleset.get_rules():
            if rule.is_discovery_rule_of(self._host) and rule.value == value:
                return rule
        return None

    def _get_table_target(self, table_source, check_type, item):
        if self._fixall:
            if table_source == self.SERVICE_VANISHED:
                return self.SERVICE_REMOVED
            elif table_source == self.SERVICE_IGNORED:
                return self.SERVICE_IGNORED
            #table_source in [self.SERVICE_MONITORED, self.SERVICE_UNDECIDED]
            return self.SERVICE_MONITORED

        bulk_target = None
        for target in [
                self.SERVICE_MONITORED,
                self.SERVICE_UNDECIDED,
                self.SERVICE_IGNORED,
                self.SERVICE_REMOVED,
        ]:
            if html.has_var("_bulk_%s_%s" % (table_source, target)):
                bulk_target = target
                break
        checkbox_var_value = html.var(self._checkbox_name(check_type, item))
        if bulk_target and (checkbox_var_value == "on" or not self._show_checkboxes):
            return bulk_target
        elif checkbox_var_value:
            return checkbox_var_value
        return table_source

    #.
    #   .--page helper---------------------------------------------------------.

    def _show_action_buttons(self, check_table):
        if not config.user.may("wato.services"):
            return

        fixall = 0
        already_has_services = False
        for check in check_table:
            if check[0] in [self.SERVICE_MONITORED, self.SERVICE_VANISHED]:
                already_has_services = True
            if check[0] in [self.SERVICE_UNDECIDED, self.SERVICE_VANISHED]:
                fixall += 1

        if fixall >= 1:
            html.button("_fixall", _("Fix all missing/vanished"))

        if already_has_services:
            html.button("_refresh", _("Automatic refresh (tabula rasa)"))

        html.button("_scan", _("Full scan"))
        if not self._show_checkboxes:
            checkbox_uri = html.makeuri([('_show_checkboxes', '1'),
                                         ('selection', weblib.selection_id())])
            checkbox_title = _('Show checkboxes')
        else:
            checkbox_uri = html.makeuri([('_show_checkboxes', '0')])
            checkbox_title = _('Hide checkboxes')

        html.buttonlink(checkbox_uri, checkbox_title)
        if self._show_parameter_column():
            html.buttonlink(html.makeuri([("_hide_parameters", "yes")]),
                            _("Hide check parameters"))
        else:
            html.buttonlink(html.makeuri([("_hide_parameters", "no")]),
                            _("Show check parameters"))

    def _show_parameter_column(self):
        return config.user.load_file("parameter_column", False)

    def _bulk_actions(self, table_source, collect_headers):
        if not config.user.may("wato.services"):
            return

        def bulk_button(source, target, target_label, label):
            html.button("_bulk_%s_%s" % (source, target), target_label,
                        help_=_("Move %s to %s services") % (label, target))

        table.row(collect_headers=collect_headers, fixed=True)
        table.cell(css="bulkactions service_discovery", colspan=self._bulk_action_colspan())

        if self._show_checkboxes:
            label = _("selected services")
        else:
            label = _("all services")

        if table_source == self.SERVICE_MONITORED:
            if config.user.may("wato.service_discovery_to_undecided"):
                bulk_button(table_source, self.SERVICE_UNDECIDED, _("Undecided"), label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)

        elif table_source == self.SERVICE_IGNORED:
            if config.user.may("wato.service_discovery_to_monitored"):
                bulk_button(table_source, self.SERVICE_MONITORED, _("Monitor"), label)
            if config.user.may("wato.service_discovery_to_undecided"):
                bulk_button(table_source, self.SERVICE_UNDECIDED, _("Undecided"), label)

        elif table_source == self.SERVICE_VANISHED:
            if config.user.may("wato.service_discovery_to_removed"):
                html.button("_bulk_%s_removed" % table_source, _("Remove"),
                            help_=_("Remove %s services") % label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)

        elif table_source == self.SERVICE_UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                bulk_button(table_source, self.SERVICE_MONITORED, _("Monitor"), label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)

    def _check_row(self, check, show_bulk_actions):
        table_source, check_type, checkgroup, item, _paramstring, params, \
            descr, state, output, _perfdata = check

        statename = short_service_state_name(state, "")
        if statename == "":
            statename = short_service_state_name(-1)
            stateclass = "state svcstate statep"
            state = 0  # for tr class
        else:
            stateclass = "state svcstate state%s" % state

        table.row(css="data", state=state)

        self._show_bulk_checkbox(check_type, item, show_bulk_actions)
        self._show_actions(check)

        table.cell(_("State"), statename, css=stateclass)
        table.cell(_("Service"), html.attrencode(descr))
        table.cell(_("Status detail"))
        if table_source in [
                self.SERVICE_CUSTOM,
                self.SERVICE_ACTIVE,
                self.SERVICE_CUSTOM_IGNORED,
                self.SERVICE_ACTIVE_IGNORED,
        ]:
            div_id = "activecheck_%s" % descr
            html.div(html.render_icon("reload", cssclass="reloading"), id_=div_id)
            html.final_javascript("execute_active_check(%s, %s, %s, %s, %s);" % (
                json.dumps(self._host.site_id() or ''),
                json.dumps(self._host_name),
                json.dumps(check_type),
                json.dumps(item),
                json.dumps(div_id),
            ))
        else:
            html.write_text(output)

        if table_source in [self.SERVICE_ACTIVE, self.SERVICE_ACTIVE_IGNORED]:
            ctype = "check_" + check_type
        else:
            ctype = check_type
        manpage_url = watolib.folder_preserving_link([("mode", "check_manpage"),
                                                      ("check_type", ctype)])
        table.cell(_("Check plugin"), html.render_a(content=ctype, href=manpage_url))

        if self._show_parameter_column():
            table.cell(_("Check parameters"))
            self._show_check_parameters(table_source, check_type, checkgroup, params)

    def _show_bulk_checkbox(self, check_type, item, show_bulk_actions):
        if not self._show_checkboxes or not config.user.may("wato.services"):
            return

        if not show_bulk_actions:
            table.cell(css="checkbox")
            return

        table.cell(
            "<input type=button class=checkgroup name=_toggle_group"
            " onclick=\"toggle_group_rows(this);\" value=\"X\" />",
            sortable=False,
            css="checkbox")
        html.checkbox(self._checkbox_name(check_type, item),
                      True, add_attr = ['title="%s"' % _('Temporarily ignore this service')])

    def _bulk_action_colspan(self):
        colspan = 5
        if self._show_parameter_column():
            colspan += 1
        if self._show_checkboxes:
            colspan += 1
        return colspan

    def _show_actions(self, check):
        def icon_button(table_source, checkbox_name, table_target, descr_target):
            html.icon_button(html.makeactionuri([(checkbox_name, table_target), ]),
                _("Move to %s services") % descr_target, "service_to_%s" % descr_target)

        def icon_button_removed(table_source, checkbox_name):
            html.icon_button(html.makeactionuri([(checkbox_name, self.SERVICE_REMOVED), ]),
                _("Remove service"), "service_to_removed")

        def rulesets_button():
            # Link to list of all rulesets affecting this service
            html.icon_button(watolib.folder_preserving_link(
                             [("mode", "object_parameters"), ("host", self._host_name),
                              ("service", descr), ]),
                _("View and edit the parameters for this service"), "rulesets")

        def check_parameters_button():
            if table_source == self.SERVICE_MANUAL:
                url = watolib.folder_preserving_link([
                    ('mode', 'edit_ruleset'),
                    ('varname', "static_checks:" + checkgroup),
                    ('host', self._host_name),
                ])
            else:
                ruleset_name = self._get_ruleset_name(table_source, check_type, checkgroup)
                if ruleset_name is None:
                    return

                url = watolib.folder_preserving_link([
                    ("mode", "edit_ruleset"),
                    ("varname", ruleset_name),
                    ("host", self._host_name),
                    ("item", watolib.mk_repr(item)),
                ]),

            html.icon_button(url,
                _("Edit and analyze the check parameters of this service"), "check_parameters")

        def disabled_services_button():
            html.icon_button(watolib.folder_preserving_link(
                             [("mode", "edit_ruleset"), ("varname", "ignored_services"),
                              ("host", self._host_name), ("item", watolib.mk_repr(descr)), ]),
                _("Edit and analyze the disabled services rules"), "rulesets")

        table.cell(css="buttons")
        if not config.user.may("wato.services"):
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            return

        table_source, check_type, checkgroup, item, _paramstring, _params, \
            descr, _state, _output, _perfdata = check
        checkbox_name = self._checkbox_name(check_type, item)

        num_buttons = 0
        if table_source == self.SERVICE_MONITORED:
            if config.user.may("wato.service_discovery_to_undecided"):
                icon_button(table_source, checkbox_name, self.SERVICE_UNDECIDED, "undecided")
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                icon_button(table_source, checkbox_name, self.SERVICE_IGNORED, "disabled")
                num_buttons += 1

        elif table_source == self.SERVICE_IGNORED:
            if may_edit_ruleset("ignored_services"):
                if config.user.may("wato.service_discovery_to_monitored"):
                    icon_button(table_source, checkbox_name, self.SERVICE_MONITORED, "monitored")
                    num_buttons += 1
                if config.user.may("wato.service_discovery_to_ignored"):
                    icon_button(table_source, checkbox_name, self.SERVICE_UNDECIDED, "undecided")
                    num_buttons += 1
                disabled_services_button()
                num_buttons += 1

        elif table_source == self.SERVICE_VANISHED:
            if config.user.may("wato.service_discovery_to_removed"):
                icon_button_removed(table_source, checkbox_name)
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                icon_button(table_source, checkbox_name, self.SERVICE_IGNORED, "disabled")
                num_buttons += 1

        elif table_source == self.SERVICE_UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                icon_button(table_source, checkbox_name, self.SERVICE_MONITORED, "monitored")
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                icon_button(table_source, checkbox_name, self.SERVICE_IGNORED, "disabled")
                num_buttons += 1

        while num_buttons < 2:
            html.empty_icon()
            num_buttons += 1

        if table_source not in [self.SERVICE_UNDECIDED,
                                self.SERVICE_IGNORED] \
           and config.user.may('wato.rulesets'):
            rulesets_button()
            check_parameters_button()
            num_buttons += 2

        while num_buttons < 4:
            html.empty_icon()
            num_buttons += 1

    def _get_ruleset_name(self, table_source, check_type, checkgroup):
        if checkgroup == "logwatch":
            return "logwatch_rules"
        elif checkgroup:
            return "checkgroup_parameters:" + checkgroup
        elif table_source in [self.SERVICE_ACTIVE, self.SERVICE_ACTIVE_IGNORED]:
            return "active_checks:" + check_type
        return None

    def _show_check_parameters(self, table_source, check_type, checkgroup, params):
        varname = self._get_ruleset_name(table_source, check_type, checkgroup)
        if varname and watolib.g_rulespecs.exists(varname):
            rulespec = watolib.g_rulespecs.get(varname)
            try:
                if isinstance(params, dict) and "tp_computed_params" in params:
                    html.write_text(_("Timespecific parameters computed at %s") % cmk.render.date_and_time(params["tp_computed_params"]["computed_at"]))
                    html.br()
                    params = params["tp_computed_params"]["params"]
                rulespec.valuespec.validate_datatype(params, "")
                rulespec.valuespec.validate_value(params, "")
                paramtext = rulespec.valuespec.value_to_text(params)
                html.write_html(paramtext)
            except Exception, e:
                if config.debug:
                    err = traceback.format_exc()
                else:
                    err = e
                paramtext = _("Invalid check parameter: %s!") % err
                paramtext += _(" The parameter is: %r") % (params,)
                paramtext += _(" The variable name is: %s") % varname
                html.write_text(paramtext)

    #.
    #   .--common helper-------------------------------------------------------.

    def _get_check_table(self):
        options = self._options[:]
        if self._do_scan and self._already_scanned and "@scan" in options:
            options.remove("@scan")
            options = ["@noscan"] + options
        if options.count("@scan"):
            self._already_scanned = True
        return watolib.check_mk_automation(self._host.site_id(), "try-inventory", options)

    def _ordered_table_groups(self):
        return [
            # table group, show bulk actions, title, help
            (self.SERVICE_UNDECIDED,      True, _("Undecided services (currently not monitored)"),
            _("These services have been found by the service discovery but are not yet added "
              "to the monitoring. You should either decide to monitor them or to permanently "
              "disable them. If you are sure that they are just transitional, just leave them "
              "until they vanish.")), # undecided
            (self.SERVICE_VANISHED,       True, _("Vanished services (monitored, but no longer exist)"),
            _("These services had been added to the monitoring by a previous discovery "
              "but the actual items that are monitored are not present anymore. This might "
              "be due to a real failure. In that case you should leave them in the monitoring. "
              "If the actually monitored things are really not relevant for the monitoring "
              "anymore then you should remove them in order to avoid UNKNOWN services in the "
              "monitoring.")),
            (self.SERVICE_MONITORED,      True, _("Monitored services"),
            _("These services had been found by a discovery and are currently configured "
              "to be monitored.")),
            (self.SERVICE_IGNORED,        True, _("Disabled services"),
            _("These services are being discovered but have been disabled by creating a rule "
              "in the rule set <i>Disabled services</i> or <i>Disabled checks</i>.")),
            (self.SERVICE_ACTIVE,         False, _("Active checks"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call classical check plugins. They have been added by a rule in the section "
              "<i>Active checks</i> or implicitely by Check_MK.")),
            (self.SERVICE_MANUAL,         False, _("Manual checks"),
            _("These services have not been found by the discovery but have been added "
              "manually by a rule in the WATO module <i>Manual checks</i>.")),
            (self.SERVICE_LEGACY,         False, _("Legacy services (defined in main.mk)"),
            _("These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
              "in <tt>main.mk</tt> or a similar configuration file.")),
            (self.SERVICE_CUSTOM,         False, _("Custom checks (defined via rule)"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call a classical check plugin, that you have installed yourself.")),
            (self.SERVICE_CLUSTERED_OLD,  False, _("Monitored clustered services (located on cluster host)"),
            _("These services have been found on this host but have been mapped to "
              "a cluster host by a rule in the set <i>Clustered services</i>.")),
            (self.SERVICE_CLUSTERED_NEW,  False, _("Undecided clustered services"),
            _("These services have been found on this host and have been mapped to "
              "a cluster host by a rule in the set <i>Clustered services</i>, but are not "
              "yet added to the active monitoring. Please either add them or permanently disable "
              "them.")),
            (self.SERVICE_ACTIVE_IGNORED, False, _("Disabled active checks"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call classical check plugins. They have been added by a rule in the section "
              "<i>Active checks</i> or implicitely by Check_MK. "
              "These services have been disabled by creating a rule in the rule set "
              "<i>Disabled services</i> oder <i>Disabled checks</i>.")),
            (self.SERVICE_CUSTOM_IGNORED, False, _("Disabled custom checks (defined via rule)"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call a classical check plugin, that you have installed yourself. "
              "These services have been disabled by creating a rule in the rule set "
              "<i>Disabled services</i> oder <i>Disabled checks</i>.")),
            (self.SERVICE_LEGACY_IGNORED, False, _("Disabled legacy services (defined in main.mk)"),
            _("These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
              "in <tt>main.mk</tt> or a similar configuration file. "
              "These services have been disabled by creating a rule in the rule set "
              "<i>Disabled services</i> oder <i>Disabled checks</i>.")),
        ]

    # This function returns the HTTP variable name to use for a service. This needs to be unique
    # for each host. Since this text is used as variable name, it must not contain any umlauts
    # or other special characters that are disallowed by html.parse_field_storage(). Since item
    # may contain such chars, we need to use some encoded form of it. Simple escaping/encoding
    # like we use for values of variables is not enough here.
    def _checkbox_name(self, check_type, item):
        key = u"%s_%s" % (check_type, item)
        return "_move_%s" % sha256(key.encode('utf-8')).hexdigest()


class ModeFirstDiscovery(ModeDiscovery):
    pass


class ModeAjaxExecuteCheck(WatoWebApiMode):
    def _from_vars(self):
        # TODO: Validate the site
        self._site = html.var("site")

        self._host_name = html.var("host")
        self._host = watolib.Folder.current().host(self._host_name)
        if not self._host:
            raise MKGeneralException(_("You called this page with an invalid host name."))

        # TODO: Validate
        self._check_type = html.var("checktype")
        # TODO: Validate
        self._item = html.var("item")

        self._host.need_permission("read")

    def page(self):
        watolib.init_wato_datastructures(with_wato_lock=True)
        try:
            state, output = watolib.check_mk_automation(
                self._site,
                "active-check", [self._host_name, self._check_type, self._item],
                sync=False)
        except Exception, e:
            state = 3
            output = "%s" % e

        return {
            "state": state,
            "state_name": short_service_state_name(state, "UNKN"),
            "output": output,
        }


register_page_handler("wato_ajax_execute_check", lambda: ModeAjaxExecuteCheck().handle_page())
