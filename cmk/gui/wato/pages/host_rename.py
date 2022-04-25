#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for renaming one or multiple existing hosts"""

import socket
from typing import Optional, Type

from cmk.utils.regex import regex
from cmk.utils.site import omd_site

import cmk.gui.background_job as background_job
import cmk.gui.forms as forms
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.watolib as watolib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import FinalizeRequest, MKAuthException, MKGeneralException, MKUserError
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.http import request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils import flash, mode_registry, redirect, WatoMode
from cmk.gui.plugins.wato.utils.html_elements import wato_html_head
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.confirm_with_preview import confirm_with_preview
from cmk.gui.utils.urls import makeuri
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Hostname,
    ListOf,
    RegExp,
    TextInput,
    Tuple,
)
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.wato.pages.hosts import ModeEditHost, page_menu_host_entries
from cmk.gui.watolib.host_rename import perform_rename_hosts
from cmk.gui.watolib.hosts_and_folders import validate_host_uniqueness
from cmk.gui.watolib.site_changes import SiteChanges


@gui_background_job.job_registry.register
class RenameHostsBackgroundJob(watolib.WatoBackgroundJob):
    job_prefix = "rename-hosts"

    @classmethod
    def gui_title(cls):
        return _("Host renaming")

    def __init__(self, title=None):
        last_job_status = watolib.WatoBackgroundJob(self.job_prefix).get_status()
        super().__init__(
            self.job_prefix,
            title=title or self.gui_title(),
            lock_wato=True,
            stoppable=False,
            estimated_duration=last_job_status.get("duration"),
        )

        if self.is_active():
            raise MKGeneralException(_("Another renaming operation is currently in progress"))

    def _back_url(self):
        return makeuri(request, [])


@gui_background_job.job_registry.register
class RenameHostBackgroundJob(RenameHostsBackgroundJob):
    def __init__(self, host, title=None):
        super().__init__(title)
        self._host = host

    def _back_url(self):
        return self._host.folder().url()


@mode_registry.register
class ModeBulkRenameHost(WatoMode):
    @classmethod
    def name(cls):
        return "bulk_rename_host"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def __init__(self):
        super().__init__()

        if not user.may("wato.rename_hosts"):
            raise MKGeneralException(_("You don't have the right to rename hosts"))

    def title(self):
        return _("Bulk renaming of hosts")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Hosts"),
            breadcrumb,
            form_name="bulk_rename_host",
            button_name="_save",
            save_title=_("Bulk rename"),
        )

        host_renaming_job = RenameHostsBackgroundJob()
        actions_dropdown = menu.dropdowns[0]
        actions_dropdown.topics.append(
            PageMenuTopic(
                title=_("Last result"),
                entries=[
                    PageMenuEntry(
                        title=_("Show last rename result"),
                        icon_name="background_job_details",
                        item=make_simple_link(host_renaming_job.detail_url()),
                        is_enabled=host_renaming_job.is_available(),
                    ),
                ],
            )
        )

        return menu

    def action(self) -> ActionResult:
        renaming_config = self._vs_renaming_config().from_html_vars("")
        self._vs_renaming_config().validate_value(renaming_config, "")
        renamings = self._collect_host_renamings(renaming_config)

        if not renamings:
            flash(_("No matching host names"))
            return None

        warning = self._renaming_collision_error(renamings)
        if warning:
            flash(warning)
            return None

        message = html.render_b(
            _(
                "Do you really want to rename to following hosts?"
                "This involves a restart of the monitoring core!"
            )
        )

        rows = []
        for _folder, host_name, target_name in renamings:
            rows.append(
                html.render_tr(html.render_td(host_name) + html.render_td(" → %s" % target_name))
            )
        message += html.render_table(HTML().join(rows))

        nr_rename = len(renamings)
        c = _confirm(
            _("Confirm renaming of %d %s") % (nr_rename, ungettext("host", "hosts", nr_rename)),
            message,
        )
        if c:
            title = _("Renaming of %s") % ", ".join("%s → %s" % x[1:] for x in renamings)
            host_renaming_job = RenameHostsBackgroundJob(title=title)
            host_renaming_job.set_function(rename_hosts_background_job, renamings)

            try:
                host_renaming_job.start()
            except background_job.BackgroundJobAlreadyRunning as e:
                raise MKGeneralException(_("Another host renaming job is already running: %s") % e)

            return redirect(host_renaming_job.detail_url())
        if c is False:  # not yet confirmed
            return FinalizeRequest(code=200)
        return None  # browser reload

    def _renaming_collision_error(self, renamings):
        name_collisions = set()
        new_names = [new_name for _folder, _old_name, new_name in renamings]
        all_host_names = watolib.Host.all().keys()
        for name in new_names:
            if name in all_host_names:
                name_collisions.add(name)
        for name in new_names:
            if new_names.count(name) > 1:
                name_collisions.add(name)

        if name_collisions:
            warning = "<b>%s</b><ul>" % _(
                "You cannot do this renaming since the following host names would collide:"
            )
            for name in sorted(list(name_collisions)):
                warning += "<li>%s</li>" % name
            warning += "</ul>"
            return warning

    def _collect_host_renamings(self, renaming_config):
        return self._recurse_hosts_for_renaming(watolib.Folder.current(), renaming_config)

    def _recurse_hosts_for_renaming(self, folder, renaming_config):
        entries = []
        for host_name, host in folder.hosts().items():
            target_name = self._host_renamed_into(host_name, renaming_config)
            if target_name and host.may("write"):
                entries.append((folder, host_name, target_name))
        if renaming_config["recurse"]:
            for subfolder in folder.subfolders():
                entries += self._recurse_hosts_for_renaming(subfolder, renaming_config)
        return entries

    def _host_renamed_into(self, hostname, renaming_config):
        prefix_regex = regex(renaming_config["match_hostname"])
        if not prefix_regex.match(hostname):
            return None

        new_hostname = hostname
        for operation in renaming_config["renamings"]:
            new_hostname = self._host_renaming_operation(operation, new_hostname)

        if new_hostname != hostname:
            return new_hostname
        return None

    def _host_renaming_operation(self, operation, hostname):
        if operation == "drop_domain":
            return hostname.split(".", 1)[0]
        if operation == "reverse_dns":
            try:
                reverse_dns = socket.gethostbyaddr(hostname)[0]
                return reverse_dns
            except Exception:
                return hostname
        if operation == ("case", "upper"):
            return hostname.upper()
        if operation == ("case", "lower"):
            return hostname.lower()
        if operation[0] == "add_suffix":
            return hostname + operation[1]
        if operation[0] == "add_prefix":
            return operation[1] + hostname
        if operation[0] == "explicit":
            old_name, new_name = operation[1]
            if old_name == hostname:
                return new_name
            return hostname
        if operation[0] == "regex":
            match_regex, new_name = operation[1]
            match = regex(match_regex).match(hostname)
            if match:
                for nr, group in enumerate(match.groups()):
                    new_name = new_name.replace("\\%d" % (nr + 1), group)
                new_name = new_name.replace("\\0", hostname)
                return new_name
            return hostname

    def page(self):
        html.begin_form("bulk_rename_host", method="POST")
        self._vs_renaming_config().render_input("", {})
        html.hidden_fields()
        html.end_form()

    def _vs_renaming_config(self):
        return Dictionary(
            title=_("Bulk Renaming"),
            render="form",
            elements=[
                (
                    "recurse",
                    Checkbox(
                        title=_("Folder Selection"),
                        label=_("Include all subfolders"),
                        default_value=True,
                    ),
                ),
                (
                    "match_hostname",
                    RegExp(
                        title=_("Hostname matching"),
                        help=_(
                            "Only rename hostnames whose names <i>begin</i> with the regular expression entered here."
                        ),
                        mode=RegExp.complete,
                    ),
                ),
                (
                    "renamings",
                    ListOf(
                        valuespec=self._vs_host_renaming(),
                        title=_("Renaming Operations"),
                        add_label=_("Add renaming"),
                        allow_empty=False,
                    ),
                ),
            ],
            optional_keys=[],
        )

    def _vs_host_renaming(self):
        return CascadingDropdown(
            orientation="horizontal",
            choices=[
                (
                    "case",
                    _("Case translation"),
                    DropdownChoice(
                        choices=[
                            ("upper", _("Convert hostnames to upper case")),
                            ("lower", _("Convert hostnames to lower case")),
                        ]
                    ),
                ),
                ("add_suffix", _("Add Suffix"), Hostname()),
                ("add_prefix", _("Add Prefix"), Hostname()),
                ("drop_domain", _("Drop Domain Suffix")),
                ("reverse_dns", _("Convert IP addresses of hosts into host their DNS names")),
                (
                    "regex",
                    _("Regular expression substitution"),
                    Tuple(
                        help=_(
                            "Please specify a regular expression in the first field. This expression should at "
                            "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                            "In the second field you specify the translated host name and can refer to the first matched "
                            "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>"
                        ),
                        elements=[
                            RegExp(
                                title=_("Regular expression for the beginning of the host name"),
                                help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                mingroups=0,
                                maxgroups=9,
                                size=30,
                                allow_empty=False,
                                mode=RegExp.prefix,
                            ),
                            TextInput(
                                title=_("Replacement"),
                                help=_(
                                    "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups, <tt>\\0</tt> to insert to original host name"
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ],
                    ),
                ),
                (
                    "explicit",
                    _("Explicit renaming"),
                    Tuple(
                        orientation="horizontal",
                        elements=[
                            Hostname(title=_("current host name"), allow_empty=False),
                            Hostname(title=_("new host name"), allow_empty=False),
                        ],
                    ),
                ),
            ],
        )


def _confirm(html_title, message):
    if not request.has_var("_do_confirm") and not request.has_var("_do_actions"):
        # TODO: get the breadcrumb from all call sites
        wato_html_head(title=html_title, breadcrumb=Breadcrumb())
    confirm_options = [(_("Confirm"), "_do_confirm")]
    return confirm_with_preview(message, confirm_options)


def rename_hosts_background_job(renamings, job_interface=None):
    actions, auth_problems = rename_hosts(
        renamings, job_interface=job_interface
    )  # Already activates the changes!
    watolib.confirm_all_local_changes()  # All activated by the underlying rename automation
    action_txt = "".join(["<li>%s</li>" % a for a in actions])
    message = _("Renamed %d %s at the following places:<br><ul>%s</ul>") % (
        len(renamings),
        ungettext("host", "hosts", len(renamings)),
        action_txt,
    )
    if auth_problems:
        message += _(
            "The following hosts could not be renamed because of missing permissions: %s"
        ) % ", ".join(["%s (%s)" % (host_name, reason) for (host_name, reason) in auth_problems])
    job_interface.send_result_message(message)


@mode_registry.register
class ModeRenameHost(WatoMode):
    @classmethod
    def name(cls):
        return "rename_host"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditHost

    def _from_vars(self):
        host_name = request.get_ascii_input_mandatory("host")

        if not watolib.Folder.current().has_host(host_name):
            raise MKUserError("host", _("You called this page with an invalid host name."))

        if not user.may("wato.rename_hosts"):
            raise MKAuthException(_("You don't have the right to rename hosts"))

        self._host = watolib.Folder.current().load_host(host_name)
        self._host.need_permission("write")

    def title(self):
        return _("Rename %s %s") % (
            _("Cluster") if self._host.is_cluster() else _("Host"),
            self._host.name(),
        )

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Host"),
            breadcrumb,
            form_name="rename_host",
            button_name="_save",
            save_title=_("Rename"),
        )

        host_renaming_job = RenameHostsBackgroundJob()
        actions_dropdown = menu.dropdowns[0]
        actions_dropdown.topics.append(
            PageMenuTopic(
                title=_("Last result"),
                entries=[
                    PageMenuEntry(
                        title=_("Show last rename result"),
                        icon_name="background_job_details",
                        item=make_simple_link(host_renaming_job.detail_url()),
                        is_enabled=host_renaming_job.is_available(),
                    ),
                ],
            )
        )

        menu.dropdowns.append(
            PageMenuDropdown(
                name="hosts",
                title=_("Hosts"),
                topics=[
                    PageMenuTopic(
                        title=_("For this host"),
                        entries=list(page_menu_host_entries(self.name(), self._host)),
                    ),
                ],
            )
        )

        return menu

    def action(self) -> ActionResult:
        local_site = omd_site()
        renamed_host_site = self._host.site_id()
        if (
            SiteChanges(SiteChanges.make_path(local_site)).read()
            or SiteChanges(SiteChanges.make_path(renamed_host_site)).read()
        ):
            raise MKUserError(
                "newname",
                _(
                    "You cannot rename a host while you have "
                    "pending changes on the central site (%s) or the "
                    "site the host is monitored on (%s)."
                )
                % (local_site, renamed_host_site),
            )

        newname = request.var("newname")
        self._check_new_host_name("newname", newname)
        # Creating pending entry. That makes the site dirty and that will force a sync of
        # the config to that site before the automation is being done.
        host_renaming_job = RenameHostBackgroundJob(
            self._host, title=_("Renaming of %s -> %s") % (self._host.name(), newname)
        )
        renamings = [(watolib.Folder.current(), self._host.name(), newname)]
        host_renaming_job.set_function(rename_hosts_background_job, renamings)

        try:
            host_renaming_job.start()
        except background_job.BackgroundJobAlreadyRunning as e:
            raise MKGeneralException(_("Another host renaming job is already running: %s") % e)

        return redirect(host_renaming_job.detail_url())

    def _check_new_host_name(self, varname, host_name):
        if not host_name:
            raise MKUserError(varname, _("Please specify a host name."))
        if watolib.Folder.current().has_host(host_name):
            raise MKUserError(varname, _("A host with this name already exists in this folder."))
        validate_host_uniqueness(varname, host_name)
        Hostname().validate_value(host_name, varname)

    def page(self):
        html.help(
            _(
                "The renaming of hosts is a complex operation since a host's name is being "
                "used as a unique key in various places. It also involves stopping and starting "
                "of the monitoring core. You cannot rename a host while you have pending changes."
            )
        )

        html.begin_form("rename_host", method="POST")
        html.add_confirm_on_submit(
            "rename_host",
            _(
                "Are you sure you want to rename the host <b>%s</b>? "
                "This involves a restart of the monitoring core!"
            )
            % (self._host.name()),
        )
        forms.header(_("Rename host %s") % self._host.name())
        forms.section(_("Current name"))
        html.write_text(self._host.name())
        forms.section(_("New name"))
        html.text_input("newname", "")
        forms.end()
        html.set_focus("newname")
        html.hidden_fields()
        html.end_form()


# renamings is a list of tuples of (folder, oldname, newname)
def rename_hosts(renamings, job_interface=None):
    action_counts, auth_problems = perform_rename_hosts(renamings, job_interface)
    action_texts = render_renaming_actions(action_counts)
    return action_texts, auth_problems


def render_renaming_actions(action_counts):
    action_titles = {
        "folder": _("Folder"),
        "notify_user": _("Users' notification rule"),
        "notify_global": _("Global notification rule"),
        "notify_flexible": _("Flexible notification rule"),
        "wato_rules": _("Host and service configuration rule"),
        "alert_rules": _("Alert handler rule"),
        "parents": _("Parent definition"),
        "cluster_nodes": _("Cluster node definition"),
        "bi": _("BI rule or aggregation"),
        "favorites": _("Favorite entry of user"),
        "cache": _("Cached output of monitoring agent"),
        "counters": _("File with performance counter"),
        "agent": _("Baked host specific agent"),
        "agent_deployment": _("Agent deployment status"),
        "piggyback-load": _("Piggyback information from other host"),
        "piggyback-pig": _("Piggyback information for other hosts"),
        "autochecks": _("Disovered services of the host"),
        "host-labels": _("Disovered host labels of the host"),
        "logwatch": _("Logfile information of logwatch plugin"),
        "snmpwalk": _("A stored SNMP walk"),
        "rrd": _("RRD databases with performance data"),
        "rrdcached": _("RRD updates in journal of RRD Cache"),
        "pnpspool": _("Spool files of PNP4Nagios"),
        "nagvis": _("NagVis map"),
        "history": _("Monitoring history entries (events and availability)"),
        "retention": _("The current monitoring state (including acknowledgements and downtimes)"),
        "inv": _("Recent hardware/software inventory"),
        "invarch": _("History of hardware/software inventory"),
    }

    texts = []
    for what, count in sorted(action_counts.items()):
        if what.startswith("dnsfail-"):
            text = (
                _(
                    "<b>WARNING: </b> the IP address lookup of <b>%s</b> has failed. The core has been "
                    "started by using the address <tt>0.0.0.0</tt> for the while. "
                    "Please update your DNS or configure an IP address for the affected host."
                )
                % what.split("-", 1)[1]
            )
        else:
            text = action_titles.get(what, what)

        if count > 1:
            text += _(" (%d times)") % count
        texts.append(text)

    return texts
