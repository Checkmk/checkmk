#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for automatic scan of parents (similar to cmk --scan-parents)"""

from typing import Any, List, NamedTuple, Optional, Type

from livestatus import SiteId

import cmk.utils.store as store
from cmk.utils.type_defs import HostName

import cmk.gui.forms as forms
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.globals import active_config, html, request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.plugins.wato.utils import get_hosts_from_checkboxes, mode_registry, WatoMode
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.check_mk_automations import scan_parents
from cmk.gui.watolib.hosts_and_folders import CREFolder


class ParentScanTask(NamedTuple):
    site_id: SiteId
    folder_path: Any
    host_name: str


class ParentScanResult(NamedTuple):
    existing_gw_host_name: HostName
    ip: str
    dns_name: HostName


class ParentScanSettings(NamedTuple):
    where: str
    alias: str
    recurse: bool
    select: str
    timeout: int
    probes: int
    max_ttl: int
    force_explicit: bool
    ping_probes: int


# TODO: This job should be executable multiple times at once
@gui_background_job.job_registry.register
class ParentScanBackgroundJob(watolib.WatoBackgroundJob):
    job_prefix = "parent_scan"

    @classmethod
    def gui_title(cls):
        return _("Parent scan")

    def __init__(self):
        super().__init__(
            self.job_prefix,
            title=_("Parent scan"),
            lock_wato=False,
            stoppable=False,
        )

    def _back_url(self):
        return watolib.Folder.current().url()

    def do_execute(self, settings, tasks, job_interface=None):
        self._initialize_statistics()
        self._logger.info("Parent scan started...")

        for task in tasks:
            self._process_task(task, settings)

        self._logger.info("Summary:")
        for title, value in [
            ("Total hosts", self._num_hosts_total),
            ("Gateways found", self._num_gateways_found),
            ("Directly reachable hosts", self._num_directly_reachable_hosts),
            ("Unreachable gateways", self._num_unreachable_gateways),
            ("No gateway found", self._num_no_gateway_found),
            ("New parents configured", self._num_new_parents_configured),
            ("Gateway hosts created", self._num_gateway_hosts_created),
            ("Errors", self._num_errors),
        ]:
            self._logger.info("  %s: %d" % (title, value))

        job_interface.send_result_message(_("Parent scan finished"))

    def _initialize_statistics(self) -> None:
        self._num_hosts_total = 0
        self._num_gateways_found = 0
        self._num_directly_reachable_hosts = 0
        self._num_unreachable_gateways = 0
        self._num_no_gateway_found = 0
        self._num_new_parents_configured = 0
        self._num_gateway_hosts_created = 0
        self._num_errors = 0

    def _process_task(self, task: ParentScanTask, settings: ParentScanSettings) -> None:
        self._num_hosts_total += 1

        try:
            self._process_parent_scan_results(
                task, settings, self._execute_parent_scan(task, settings)
            )
        except Exception as e:
            self._num_errors += 1
            if task.site_id:
                msg = _("ERROR %s on site %s: %s") % (task.host_name, task.site_id, e)
            else:
                msg = _("ERROR %s: %s") % (task.host_name, e)

            if isinstance(e, MKUserError):
                self._logger.error(msg)
            else:
                self._logger.exception(msg)

    def _execute_parent_scan(self, task: ParentScanTask, settings: ParentScanSettings) -> List:
        return scan_parents(
            task.site_id,
            task.host_name,
            *map(
                str,
                [
                    settings.timeout,
                    settings.probes,
                    settings.max_ttl,
                    settings.ping_probes,
                ],
            ),
        ).gateways

    def _process_parent_scan_results(
        self, task: ParentScanTask, settings: ParentScanSettings, gateways: List
    ) -> None:
        gateway = ParentScanResult(*gateways[0][0]) if gateways[0][0] else None
        state, skipped_gateways, error = gateways[0][1:]

        if state in ["direct", "root", "gateway"]:
            # The following code updates the host config. The progress from loading the WATO folder
            # until it has been saved needs to be locked.
            with store.lock_checkmk_configuration():
                self._configure_host_and_gateway(task, settings, gateway)
        else:
            self._logger.error(error)

        if gateway:
            self._num_gateways_found += 1

        if state in ["direct", "root"]:
            self._num_directly_reachable_hosts += 1

        self._num_unreachable_gateways += skipped_gateways

        if state == "notfound":
            self._num_no_gateway_found += 1

        if state in ["failed", "dnserror", "garbled"]:
            self._num_errors += 1

    def _configure_host_and_gateway(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        gateway: Optional[ParentScanResult],
    ) -> None:
        watolib.Folder.invalidate_caches()
        folder = watolib.Folder.folder(task.folder_path)

        parents = self._configure_gateway(task, settings, gateway, folder)

        host = folder.host(task.host_name)
        if host.effective_attribute("parents") == parents:
            self._logger.info(
                "Parents unchanged at %s", (",".join(parents) if parents else _("none"))
            )
            return

        if settings.force_explicit or host.folder().effective_attribute("parents") != parents:
            host.update_attributes({"parents": parents})
        else:
            # Check which parents the host would have inherited
            if host.has_explicit_attribute("parents"):
                host.clean_attributes(["parents"])

        if parents:
            self._logger.info("Set parents to %s", ",".join(parents))
        else:
            self._logger.info("Removed parents")

        self._num_new_parents_configured += 1

    def _configure_gateway(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        gateway: Optional[ParentScanResult],
        folder: CREFolder,
    ) -> List[HostName]:
        """Ensure there is a gateway host in the Check_MK configuration (or raise an exception)

        If we have found a gateway, we need to know a matching host name from our configuration.
        If there is none, we can create one, if the users wants this. The automation for the parent
        scan already tries to find such a host within the site."""
        if not gateway:
            return []

        if gateway.existing_gw_host_name:
            return [gateway.existing_gw_host_name]  # Nothing needs to be created

        if settings.where == "nowhere":
            raise MKUserError(None, _("Need parent %s, but not allowed to create one") % gateway.ip)

        gw_folder = self._determine_gateway_folder(settings.where, folder)
        gw_host_name = self._determine_gateway_host_name(task, gateway)
        gw_host_attributes = self._determine_gateway_attributes(task, settings, gateway, gw_folder)

        gw_folder.create_hosts([(gw_host_name, gw_host_attributes, None)])
        self._num_gateway_hosts_created += 1

        return [gw_host_name]

    def _determine_gateway_folder(self, where: str, folder: CREFolder) -> CREFolder:
        if where == "here":  # directly in current folder
            return watolib.Folder.current_disk_folder()

        if where == "subfolder":
            current = watolib.Folder.current_disk_folder()

            # Put new gateways in subfolder "Parents" of current
            # folder. Does this folder already exist?
            if current.has_subfolder("parents"):
                return current.subfolder("parents")
            # Create new gateway folder
            return current.create_subfolder("parents", _("Parents"), {})

        if where == "there":  # In same folder as host
            return folder

        raise NotImplementedError()

    def _determine_gateway_host_name(
        self, task: ParentScanTask, gateway: ParentScanResult
    ) -> HostName:
        if gateway.dns_name:
            return gateway.dns_name

        if task.site_id:
            return HostName("gw-%s-%s" % (task.site_id, gateway.ip.replace(".", "-")))

        return HostName("gw-%s" % (gateway.ip.replace(".", "-")))

    def _determine_gateway_attributes(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        gateway: ParentScanResult,
        gw_folder: CREFolder,
    ) -> dict:
        new_host_attributes = {
            "ipaddress": gateway.ip,
        }

        if settings.alias:
            new_host_attributes["alias"] = settings.alias

        if gw_folder.site_id() != task.site_id:
            new_host_attributes["site"] = task.site_id

        return new_host_attributes


@mode_registry.register
class ModeParentScan(WatoMode):
    @classmethod
    def name(cls):
        return "parentscan"

    @classmethod
    def permissions(cls):
        return ["hosts", "parentscan"]

    def title(self):
        return _("Parent scan")

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def _from_vars(self):
        self._start = bool(request.var("_start"))
        # 'all' not set -> only scan checked hosts in current folder, no recursion
        # otherwise: all host in this folder, maybe recursively
        self._all = bool(request.var("all"))
        self._complete_folder = self._all

        # Ignored during initial form display
        self._settings = ParentScanSettings(
            where=request.get_ascii_input_mandatory("where", "subfolder"),
            alias=request.get_str_input_mandatory("alias", "").strip(),
            recurse=html.get_checkbox("recurse") or False,
            select=request.get_ascii_input_mandatory("select", "noexplicit"),
            timeout=request.get_integer_input_mandatory("timeout", 8),
            probes=request.get_integer_input_mandatory("probes", 2),
            max_ttl=request.get_integer_input_mandatory("max_ttl", 10),
            force_explicit=html.get_checkbox("force_explicit") or False,
            ping_probes=request.get_integer_input_mandatory("ping_probes", 5),
        )
        self._job = ParentScanBackgroundJob()

    def action(self) -> ActionResult:
        try:
            transactions.check_transaction()
            user.save_file("parentscan", dict(self._settings._asdict()))

            self._job.set_function(self._job.do_execute, self._settings, self._get_tasks())
            self._job.start()
        except Exception as e:
            if active_config.debug:
                raise
            logger.exception("Failed to start parent scan")
            raise MKUserError(
                None, _("Failed to start parent scan: %s") % ("%s" % e).replace("\n", "\n<br>")
            )

        raise HTTPRedirect(self._job.detail_url())

    def _get_tasks(self):
        if not request.var("all"):
            return self._get_current_folder_host_tasks()
        return self._get_folder_tasks()

    def _get_current_folder_host_tasks(self):
        """only scan checked hosts in current folder, no recursion"""
        tasks = []
        for host in get_hosts_from_checkboxes():
            if self._include_host(host, self._settings.select):
                tasks.append(ParentScanTask(host.site_id(), host.folder().path(), host.name()))
        return tasks

    def _get_folder_tasks(self):
        """all host in this folder, probably recursively"""
        tasks = []
        for host in self._recurse_hosts(
            watolib.Folder.current(), self._settings.recurse, self._settings.select
        ):
            tasks.append(ParentScanTask(host.site_id(), host.folder().path(), host.name()))
        return tasks

    # select: 'noexplicit' -> no explicit parents
    #         'no'         -> no implicit parents
    #         'ignore'     -> not important
    def _include_host(self, host, select):
        if select == "noexplicit" and host.has_explicit_attribute("parents"):
            return False
        if select == "no":
            if host.effective_attribute("parents"):
                return False
        return True

    def _recurse_hosts(self, folder, recurse, select):
        entries = []
        for host in folder.hosts().values():
            if self._include_host(host, select):
                entries.append(host)

        if recurse:
            for subfolder in folder.subfolders():
                entries += self._recurse_hosts(subfolder, recurse, select)
        return entries

    def page(self):
        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_active():
            html.show_message(
                _('Parent scan currently running in <a href="%s">background</a>.')
                % self._job.detail_url()
            )
            return

        self._show_start_form()

    # TODO: Refactor to be valuespec based
    def _show_start_form(self):
        html.begin_form("parentscan", method="POST")
        html.hidden_fields()

        # Mode of action
        html.open_p()
        if not self._complete_folder:
            num_selected = len(get_hosts_from_checkboxes())
            html.write_text(_("You have selected <b>%d</b> hosts for parent scan. ") % num_selected)
        html.p(
            _(
                "The parent scan will try to detect the last gateway "
                "on layer 3 (IP) before a host. This will be done by "
                "calling <tt>traceroute</tt>. If a gateway is found by "
                "that way and its IP address belongs to one of your "
                "monitored hosts, that host will be used as the hosts "
                "parent. If no such host exists, an artifical ping-only "
                "gateway host will be created if you have not disabled "
                "this feature."
            )
        )

        forms.header(_("Settings for Parent Scan"))

        self._settings = ParentScanSettings(
            **user.load_file(
                "parentscan",
                {
                    "where": "subfolder",
                    "alias": _("Created by parent scan"),
                    "recurse": True,
                    "select": "noexplicit",
                    "timeout": 8,
                    "probes": 2,
                    "ping_probes": 5,
                    "max_ttl": 10,
                    "force_explicit": False,
                },
            )
        )

        # Selection
        forms.section(_("Selection"))
        if self._complete_folder:
            html.checkbox("recurse", self._settings.recurse, label=_("Include all subfolders"))
            html.br()
        html.radiobutton(
            "select",
            "noexplicit",
            self._settings.select == "noexplicit",
            _("Skip hosts with explicit parent definitions (even if empty)") + "<br>",
        )
        html.radiobutton(
            "select",
            "no",
            self._settings.select == "no",
            _("Skip hosts hosts with non-empty parents (also if inherited)") + "<br>",
        )
        html.radiobutton(
            "select", "ignore", self._settings.select == "ignore", _("Scan all hosts") + "<br>"
        )

        # Performance
        forms.section(_("Performance"))
        html.open_table()
        html.open_tr()
        html.open_td()
        html.write_text(_("Timeout for responses") + ":")
        html.close_td()
        html.open_td()
        html.text_input("timeout", str(self._settings.timeout), size=2, cssclass="number")
        html.write_text(_("sec"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of probes per hop") + ":")
        html.close_td()
        html.open_td()
        html.text_input("probes", str(self._settings.probes), size=2, cssclass="number")
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Maximum distance (TTL) to gateway") + ":")
        html.close_td()
        html.open_td()
        html.text_input("max_ttl", str(self._settings.max_ttl), size=2, cssclass="number")
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of PING probes") + ":")
        html.help(
            _(
                "After a gateway has been found, Check_MK checks if it is reachable "
                "via PING. If not, it is skipped and the next gateway nearer to the "
                "monitoring core is being tried. You can disable this check by setting "
                "the number of PING probes to 0."
            )
        )
        html.close_td()
        html.open_td()
        html.text_input("ping_probes", str(self._settings.ping_probes), size=2, cssclass="number")
        html.close_td()
        html.close_tr()
        html.close_table()

        # Configuring parent
        forms.section(_("Configuration"))
        html.checkbox(
            "force_explicit",
            deflt=self._settings.force_explicit,
            label=_(
                "Force explicit setting for parents even if setting matches that of the folder"
            ),
        )

        # Gateway creation
        forms.section(_("Creation of gateway hosts"))
        html.write_text(_("Create gateway hosts in"))
        html.open_ul()

        html.radiobutton(
            "where",
            "subfolder",
            self._settings.where == "subfolder",
            _("in the subfolder <b>%s/Parents</b>") % watolib.Folder.current_disk_folder().title(),
        )

        html.br()
        html.radiobutton(
            "where",
            "here",
            self._settings.where == "here",
            _("directly in the folder <b>%s</b>") % watolib.Folder.current_disk_folder().title(),
        )
        html.br()
        html.radiobutton(
            "where", "there", self._settings.where == "there", _("in the same folder as the host")
        )
        html.br()
        html.radiobutton(
            "where", "nowhere", self._settings.where == "nowhere", _("do not create gateway hosts")
        )
        html.close_ul()
        html.write_text(_("Alias for created gateway hosts") + ": ")
        html.text_input("alias", default_value=self._settings.alias)

        forms.end()

        # Start button
        html.button("_start", _("Start"))
        html.hidden_fields()
        html.end_form()
