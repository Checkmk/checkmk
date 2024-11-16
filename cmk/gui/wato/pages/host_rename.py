#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for renaming one or multiple existing hosts"""

import socket
from collections.abc import Collection, Iterable, Mapping, Sequence
from functools import partial
from typing import Any

from cmk.ccc import version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import edition_supports_nagvis

from cmk.utils import paths
from cmk.utils.global_ident_type import is_locked_by_quick_setup
from cmk.utils.hostaddress import HostName
from cmk.utils.regex import regex

from cmk.gui import forms
from cmk.gui.background_job import BackgroundProcessInterface, InitialStatusArgs
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import FinalizeRequest, MKAuthException, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.type_defs import RequireConfirmation
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
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.confirm_with_preview import confirm_with_preview
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
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
from cmk.gui.wato.pages._html_elements import wato_html_head
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.wato.pages.hosts import ModeEditHost, page_menu_host_entries
from cmk.gui.watolib.activate_changes import ActivateChanges
from cmk.gui.watolib.host_rename import (
    group_renamings_by_site,
    perform_rename_hosts,
    RenameHostBackgroundJob,
    RenameHostsBackgroundJob,
)
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    folder_from_request,
    folder_tree,
    Host,
    validate_host_uniqueness,
)
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeBulkRenameHost)
    mode_registry.register(ModeRenameHost)


class HostRenamingException(MKGeneralException):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ModeBulkRenameHost(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "bulk_rename_host"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_hosts"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    def __init__(self) -> None:
        super().__init__()

        if not user.may("wato.rename_hosts"):
            raise MKGeneralException(_("You don't have the right to rename hosts"))

    def title(self) -> str:
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
        check_csrf_token()

        renaming_config = self._vs_renaming_config().from_html_vars("")
        self._vs_renaming_config().validate_value(renaming_config, "")
        try:
            renamings = self._collect_host_renamings(renaming_config)
        except HostRenamingException as e:
            flash(e.message)
            return None

        message = HTMLWriter.render_b(
            _(
                "Do you really want to rename the following hosts? "
                "This involves a restart of the monitoring core and blocks %s "
                "until the next activation!"
            )
            % HTMLWriter.render_tt("Discard Changes")
        )

        rows = []
        for _folder, host_name, target_name in renamings:
            rows.append(
                HTMLWriter.render_tr(
                    HTMLWriter.render_td(host_name) + HTMLWriter.render_td(" → %s" % target_name)
                )
            )
        message += HTMLWriter.render_table(HTML.empty().join(rows))

        nr_rename = len(renamings)
        c = _confirm(
            _("Confirm renaming of %d %s") % (nr_rename, ungettext("host", "hosts", nr_rename)),
            message,
        )
        if c:
            title = _("Renaming of %s") % ", ".join("%s → %s" % x[1:] for x in renamings)
            host_renaming_job = RenameHostsBackgroundJob()
            if (
                result := host_renaming_job.start(
                    partial(rename_hosts_background_job, _renamings_to_job_args(renamings)),
                    InitialStatusArgs(
                        title=title,
                        lock_wato=True,
                        stoppable=False,
                        estimated_duration=host_renaming_job.get_status().duration,
                        user=str(user.id) if user.id else None,
                    ),
                )
            ).is_error():
                raise MKGeneralException(result.error)

            return redirect(host_renaming_job.detail_url())
        if c is False:  # not yet confirmed
            return FinalizeRequest(code=200)
        return None  # browser reload

    @staticmethod
    def _format_renamings_warning(message: str, values: Iterable[str]) -> str:
        values_list = "".join(f"<li>{value}</li>" for value in sorted(values))
        return f"<b>{message}</b><ul>{values_list}</ul>"

    def _validate_renamings(
        self, renamings: list[tuple[Folder, HostName, str]]
    ) -> list[tuple[Folder, HostName, HostName]]:
        """Check if the new names are valid host names and do not collide with existing hosts.
        Return a new list of renamings."""
        invalid_names = set()
        name_collisions = set()
        seen_names = set()
        locked_by_quick_setup = set()
        all_host_names = Host.all().keys()
        updated_renamings = []
        for folder, old_name, new_name in renamings:
            if new_name in seen_names or new_name in all_host_names:
                name_collisions.add(new_name)
            seen_names.add(new_name)
            try:
                updated_renamings.append((folder, old_name, HostName(new_name)))
            except ValueError:
                invalid_names.add(new_name)

            if (host := folder.host(old_name)) and is_locked_by_quick_setup(host.locked_by()):
                locked_by_quick_setup.add(old_name)

        warning = ""
        if invalid_names:
            warning += self._format_renamings_warning(
                _("You cannot do this renaming since the following host names would be invalid:"),
                invalid_names,
            )
        if name_collisions:
            warning += self._format_renamings_warning(
                _("You cannot do this renaming since the following host names would collide:"),
                name_collisions,
            )
        if locked_by_quick_setup:
            warning += self._format_renamings_warning(
                _(
                    "You cannot do this renaming since the following hosts are locked by "
                    "Quick setup:"
                ),
                locked_by_quick_setup,
            )
        if warning:
            raise HostRenamingException(warning)

        return updated_renamings

    def _collect_host_renamings(
        self, renaming_config: dict[str, Any]
    ) -> list[tuple[Folder, HostName, HostName]]:
        unchecked = self._recurse_hosts_for_renaming(
            folder_from_request(request.var("folder"), request.get_ascii_input("host")),
            renaming_config,
        )
        if not unchecked:
            raise HostRenamingException(_("No matching host names"))

        return self._validate_renamings(unchecked)

    def _recurse_hosts_for_renaming(
        self, folder: Folder, renaming_config: dict[str, Any]
    ) -> list[tuple[Folder, HostName, str]]:
        entries = []
        for host_name, host in folder.hosts().items():
            target_name = self._host_renamed_into(host_name, renaming_config)
            if target_name and host.permissions.may("write"):
                entries.append((folder, host_name, target_name))
        if renaming_config["recurse"]:
            for subfolder in folder.subfolders():
                entries += self._recurse_hosts_for_renaming(subfolder, renaming_config)
        return entries

    def _host_renamed_into(self, hostname: str, renaming_config: dict[str, Any]) -> str | None:
        prefix_regex = regex(renaming_config["match_hostname"])
        if not prefix_regex.match(hostname):
            return None

        new_hostname = hostname
        for operation in renaming_config["renamings"]:
            if (result := self._host_renaming_operation(operation, new_hostname)) is not None:
                new_hostname = result
            else:
                return None

        if new_hostname != hostname:
            return new_hostname
        return None

    def _host_renaming_operation(self, operation: Any, hostname: str) -> str | None:
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
        return None

    def page(self) -> None:
        with html.form_context("bulk_rename_host", method="POST"):
            self._vs_renaming_config().render_input("", {})
            html.hidden_fields()

    def _vs_renaming_config(self):
        return Dictionary(
            title=_("Bulk renaming"),
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
                        title=_("Host name matching"),
                        help=_(
                            "Only rename host names whose names <i>begin</i> with the regular expression entered here."
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
                            ("upper", _("Convert host names to upper case")),
                            ("lower", _("Convert host names to lower case")),
                        ]
                    ),
                ),
                ("add_suffix", _("Add Suffix"), TextInput(allow_empty=False, size=38)),
                ("add_prefix", _("Add Prefix"), TextInput(allow_empty=False, size=38)),
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


def rename_hosts_background_job(
    renaming_args: Sequence[tuple[str, HostName, HostName]],
    job_interface: BackgroundProcessInterface,
) -> None:
    with job_interface.gui_context():
        renamings = _renamings_from_job_args(renaming_args)
        actions, auth_problems = _rename_hosts(
            renamings, job_interface
        )  # Already activates the changes!

        for site_id in group_renamings_by_site(renamings):
            ActivateChanges().confirm_site_changes(site_id)

        action_txt = "".join(["<li>%s</li>" % a for a in actions])
        message = _("Renamed %d %s at the following places:<br><ul>%s</ul>") % (
            len(renamings),
            ungettext("host", "hosts", len(renamings)),
            action_txt,
        )
        if auth_problems:
            message += _(
                "The following hosts could not be renamed because of missing permissions: %s"
            ) % ", ".join([f"{host_name} ({reason})" for (host_name, reason) in auth_problems])
        job_interface.send_result_message(message)


class ModeRenameHost(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "rename_host"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_hosts"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditHost

    def _from_vars(self) -> None:
        host_name = request.get_validated_type_input_mandatory(HostName, "host")

        folder = folder_from_request(request.var("folder"), host_name)
        if not folder.has_host(host_name):
            raise MKUserError("host", _("You called this page with an invalid host name."))

        if not user.may("wato.rename_hosts"):
            raise MKAuthException(_("You don't have the right to rename hosts"))

        self._host = folder.load_host(host_name)
        self._host.permissions.need_permission("write")

    def title(self) -> str:
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
        renamed_host_site = self._host.site_id()
        if ActivateChanges().get_pending_changes_info().has_changes():
            raise MKUserError(
                "newname",
                _(
                    "You cannot rename a host while you have "
                    "pending changes on the site the host is monitored on (%s)."
                )
                % renamed_host_site,
            )
        if is_locked_by_quick_setup(self._host.locked_by()):
            raise MKUserError(
                "host",
                _('You cannot rename host "%s", because it is managed by Quick setup.')
                % self._host.name(),
            )

        newname = request.get_validated_type_input_mandatory(HostName, "newname")
        folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        self._check_new_host_name(folder, "newname", newname)
        # Creating pending entry. That makes the site dirty and that will force a sync of
        # the config to that site before the automation is being done.
        host_renaming_job = RenameHostBackgroundJob(self._host)
        renamings = [(folder, self._host.name(), newname)]

        if (
            result := host_renaming_job.start(
                partial(rename_hosts_background_job, _renamings_to_job_args(renamings)),
                InitialStatusArgs(
                    title=_("Renaming of %s -> %s") % (self._host.name(), newname),
                    lock_wato=True,
                    stoppable=False,
                    estimated_duration=host_renaming_job.get_status().duration,
                    user=str(user.id) if user.id else None,
                ),
            )
        ).is_error():
            raise MKGeneralException(result.error)

        return redirect(host_renaming_job.detail_url())

    def _check_new_host_name(self, folder: Folder, varname: str, host_name: HostName) -> None:
        if not host_name:
            raise MKUserError(varname, _("Please specify a host name."))
        if folder.has_host(host_name):
            raise MKUserError(varname, _("A host with this name already exists in this folder."))
        validate_host_uniqueness(varname, host_name)
        Hostname().validate_value(host_name, varname)

    def page(self) -> None:
        html.help(
            _(
                "The renaming of hosts is a complex operation since a host's name is being "
                "used as a unique key in various places. It also involves stopping and starting "
                "of the monitoring core. You cannot rename a host while you have pending changes."
            )
        )

        with html.form_context(
            "rename_host",
            method="POST",
            require_confirmation=RequireConfirmation(
                html=_(
                    "Rename host?<br>"
                    "Info: Renaming the host includes a restart of the monitoring core. "
                    "While this change is pending on the central site, the reverting of pending "
                    "changes is blocked."
                ),
                confirmButtonText=_("Yes, rename"),
                cancelButtonText=_("No, keep current name"),
            ),
        ):
            forms.header(_("Rename host %s") % self._host.name())
            forms.section(_("Current name"))
            html.write_text_permissive(self._host.name())
            forms.section(_("New name"))
            html.text_input("newname", "")
            forms.end()
            html.set_focus("newname")
            html.hidden_fields()


def _renamings_to_job_args(
    renamings: Sequence[tuple[Folder, HostName, HostName]],
) -> Sequence[tuple[str, HostName, HostName]]:
    return [(folder.path(), old_name, new_name) for folder, old_name, new_name in renamings]


def _renamings_from_job_args(
    rename_args: Sequence[tuple[str, HostName, HostName]],
) -> Sequence[tuple[Folder, HostName, HostName]]:
    tree = folder_tree()
    return [
        (tree.folder(folder_path), old_name, new_name)
        for folder_path, old_name, new_name in rename_args
    ]


def _rename_hosts(
    renamings: Sequence[tuple[Folder, HostName, HostName]],
    job_interface: BackgroundProcessInterface,
) -> tuple[list[str], list[tuple[HostName, MKAuthException]]]:
    action_counts, auth_problems = perform_rename_hosts(renamings, job_interface)
    action_texts = render_renaming_actions(action_counts)
    return action_texts, auth_problems


def render_renaming_actions(action_counts: Mapping[str, int]) -> list[str]:
    action_titles = {
        "folder": _("Folder"),
        "notify_user": _("Users' notification rule"),
        "notify_global": _("Global notification rule"),
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
        "logwatch": _("Logfile information of logwatch plug-in"),
        "snmpwalk": _("A stored SNMP walk"),
        "rrd": _("RRD databases with performance data"),
        "rrdcached": _("RRD updates in journal of RRD Cache"),
        "pnpspool": _("Spool files of PNP4Nagios"),
        "history": _("Monitoring history entries (events and availability)"),
        "retention": _("The current monitoring state (including acknowledgements and downtimes)"),
        "inv": _("HW/SW Inventory"),
        "invarch": _("HW/SW Inventory history"),
        "uuid_link": _("UUID links for TLS-encrypting agent communication"),
    }

    if edition_supports_nagvis(version.edition(paths.omd_root)):
        action_titles["nagvis"] = _("NagVis map")

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
