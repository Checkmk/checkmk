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
"""When the user wants to scan the services of multiple hosts at once
this mode is used."""

import copy
from collections import namedtuple

import cmk.paths

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.log import logger
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
import cmk.gui.gui_background_job as gui_background_job

from cmk.gui.plugins.wato import (
    WatoMode,
    WatoBackgroundJob,
    mode_registry,
)

DiscoveryTask = namedtuple("DiscoveryTask", ["site_id", "folder_path", "host_names"])


# TODO: This job should be executable multiple times at once
@gui_background_job.job_registry.register
class BulkDiscoveryBackgroundJob(WatoBackgroundJob):
    job_prefix = "bulk_discovery"
    gui_title = _("Bulk Discovery")

    def __init__(self):
        kwargs = {}
        kwargs["title"] = _("Bulk discovery")
        kwargs["lock_wato"] = False
        kwargs["deletable"] = False
        kwargs["stoppable"] = False

        super(BulkDiscoveryBackgroundJob, self).__init__(self.job_prefix, **kwargs)

    def _back_url(self):
        return watolib.Folder.current().url()

    def do_execute(self, mode, use_cache, do_scan, error_handling, tasks, job_interface=None):
        self._initialize_statistics()
        job_interface.send_progress_update(_("Bulk discovery started..."))

        for task in tasks:
            self._bulk_discover_item(task, mode, use_cache, do_scan, error_handling, job_interface)

        job_interface.send_progress_update(_("Bulk discovery finished."))

        job_interface.send_progress_update(
            _("Hosts: %d total, %d succeeded, %d skipped, %d failed") %
            (self._num_hosts_total, self._num_hosts_succeeded, self._num_hosts_skipped,
             self._num_hosts_failed))
        job_interface.send_progress_update(
            _("Services: %d total, %d added, %d removed, %d kept") %
            (self._num_services_total, self._num_services_added, self._num_services_removed,
             self._num_services_kept))

        job_interface.send_result_message(_("Bulk discovery successful"))

    def _initialize_statistics(self):
        self._num_hosts_total = 0
        self._num_hosts_succeeded = 0
        self._num_hosts_skipped = 0
        self._num_hosts_failed = 0
        self._num_services_added = 0
        self._num_services_removed = 0
        self._num_services_kept = 0
        self._num_services_total = 0

    def _bulk_discover_item(self, task, mode, use_cache, do_scan, error_handling, job_interface):
        self._num_hosts_total += len(task.host_names)

        try:
            counts, failed_hosts = self._execute_discovery(task, mode, use_cache, do_scan,
                                                           error_handling)
            self._process_discovery_results(task, job_interface, counts, failed_hosts)
        except Exception:
            self._num_hosts_failed += len(task.host_names)
            if task.site_id:
                msg = _("Error during discovery of %s on site %s") % \
                    (", ".join(task.host_names), task.site_id)
            else:
                msg = _("Error during discovery of %s") % (", ".join(task.host_names))
            self._logger.exception(msg)

    def _execute_discovery(self, task, mode, use_cache, do_scan, error_handling):
        arguments = [mode] + task.host_names

        if use_cache:
            arguments = ["@cache"] + arguments
        if do_scan:
            arguments = ["@scan"] + arguments
        if not error_handling:
            arguments = ["@raiseerrors"] + arguments

        timeout = html.request.request_timeout - 2

        counts, failed_hosts = watolib.check_mk_automation(
            task.site_id, "inventory", arguments, timeout=timeout)

        return counts, failed_hosts

    def _process_discovery_results(self, task, job_interface, counts, failed_hosts):
        try:
            # The following code updates the host config. The progress from loading the WATO folder
            # until it has been saved needs to be locked.
            watolib.lock_exclusive()

            watolib.Folder.invalidate_caches()
            folder = watolib.Folder.folder(task.folder_path)

            for hostname in task.host_names:
                self._process_service_counts_for_host(counts[hostname])
                msg = self._process_discovery_result_for_host(
                    folder.host(hostname), failed_hosts.get(hostname, False), counts[hostname])
                job_interface.send_progress_update("%s: %s" % (hostname, msg))

        finally:
            watolib.unlock_exclusive()

    def _process_service_counts_for_host(self, host_counts):
        self._num_services_added += host_counts[0]
        self._num_services_removed += host_counts[1]
        self._num_services_kept += host_counts[2]
        self._num_services_total += host_counts[3]

    def _process_discovery_result_for_host(self, host, failed_reason, host_counts):
        if failed_reason is None:
            self._num_hosts_skipped += 1
            return _("discovery skipped: host not monitored")

        if failed_reason is not False:
            self._num_hosts_failed += 1
            if not host.locked():
                host.set_discovery_failed()
            return _("discovery failed: %s") % failed_reason

        self._num_hosts_succeeded += 1

        watolib.add_service_change(
            host, "bulk-discovery",
            _("Did service discovery on host %s: %d added, %d removed, %d kept, "
              "%d total services") % tuple([host.name()] + host_counts))

        if not host.locked():
            host.clear_discovery_failed()

        return _("discovery successful")


@mode_registry.register
class ModeBulkDiscovery(WatoMode):
    @classmethod
    def name(cls):
        return "bulkinventory"

    @classmethod
    def permissions(cls):
        return ["hosts", "services"]

    def _from_vars(self):
        self._start = bool(html.var("_start"))
        self._all = bool(html.var("all"))
        self._just_started = False
        self._get_bulk_discovery_params()
        self._job = BulkDiscoveryBackgroundJob()

    def _get_bulk_discovery_params(self):
        self._bulk_discovery_params = copy.deepcopy(config.bulk_discovery_default_settings)

        if self._start:
            # Only do this when the start form has been submitted
            bulk_discover_params = cmk.gui.plugins.wato.vs_bulk_discovery().from_html_vars(
                "bulkinventory")
            cmk.gui.plugins.wato.vs_bulk_discovery().validate_value(bulk_discover_params,
                                                                    "bulkinventory")
            self._bulk_discovery_params.update(bulk_discover_params)

        self._recurse, self._only_failed, self._only_failed_invcheck, \
            self._only_ok_agent = self._bulk_discovery_params["selection"]
        self._use_cache, self._do_scan, self._bulk_size = \
            self._bulk_discovery_params["performance"]
        self._mode = self._bulk_discovery_params["mode"]
        self._error_handling = self._bulk_discovery_params["error_handling"]

    def title(self):
        return _("Bulk Service Discovery")

    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")

    def action(self):
        config.user.need_permission("wato.services")

        tasks = self._get_tasks(self._get_hosts_to_discover())

        try:
            html.check_transaction()
            self._job.set_function(self._job.do_execute, self._mode, self._use_cache, self._do_scan,
                                   self._error_handling, tasks)
            self._job.start()
        except Exception, e:
            if config.debug:
                raise
            logger.exception("Failed to start bulk discovery")
            raise MKUserError(
                None,
                _("Failed to start discovery: %s") % ("%s" % e).replace("\n", "\n<br>"))

        html.response.http_redirect(self._job.detail_url())

    def page(self):
        config.user.need_permission("wato.services")

        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_running():
            html.message(
                _("Bulk discovery currently running in <a href=\"%s\">background</a>.") %
                self._job.detail_url())
            return

        self._show_start_form()

    def _show_start_form(self):
        html.begin_form("bulkinventory", method="POST")

        msgs = []
        if self._all:
            vs = cmk.gui.plugins.wato.vs_bulk_discovery(render_form=True)
        else:
            # "Include subfolders" does not make sense for a selection of hosts
            # which is already given in the following situations:
            # - in the current folder below 'Selected hosts: Discovery'
            # - Below 'Bulk import' a automatic service discovery for
            #   imported/selected hosts can be executed
            vs = cmk.gui.plugins.wato.vs_bulk_discovery(render_form=True, include_subfolders=False)
            msgs.append(
                _("You have selected <b>%d</b> hosts for bulk discovery.") % len(
                    self._get_hosts_to_discover()))
            selection = self._bulk_discovery_params["selection"]
            self._bulk_discovery_params["selection"] = [False] + list(selection[1:])

        msgs.append(
            _("Check_MK service discovery will automatically find and "
              "configure services to be checked on your hosts."))
        html.open_p()
        html.write_text(" ".join(msgs))
        vs.render_input("bulkinventory", self._bulk_discovery_params)
        forms.end()

        html.button("_start", _("Start"))
        html.hidden_fields()
        html.end_form()

    def _get_hosts_to_discover(self):
        if self._only_failed_invcheck:
            restrict_to_hosts = self._find_hosts_with_failed_discovery_check()
        else:
            restrict_to_hosts = None

        if self._only_ok_agent:
            skip_hosts = self._find_hosts_with_failed_agent()
        else:
            skip_hosts = []

        # 'all' not set -> only inventorize checked hosts
        hosts_to_discover = []

        if not self._all:
            if self._only_failed:
                filterfunc = lambda host: host.discovery_failed()
            else:
                filterfunc = None

            for host_name in watolib.get_hostnames_from_checkboxes(filterfunc):
                if restrict_to_hosts and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = watolib.Folder.current().host(host_name)
                host.need_permission("write")
                hosts_to_discover.append((host.site_id(), host.folder(), host_name))

        else:
            # all host in this folder, maybe recursively. New: we always group
            # a bunch of subsequent hosts of the same folder into one item.
            # That saves automation calls and speeds up mass inventories.
            entries = self._recurse_hosts(watolib.Folder.current())
            for host_name, folder in entries:
                if restrict_to_hosts != None and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = folder.host(host_name)
                host.need_permission("write")
                hosts_to_discover.append((host.site_id(), host.folder(), host_name))

        return sorted(hosts_to_discover)

    def _get_tasks(self, hosts_to_discover):
        """Create a list of tasks for the job

        Each task groups the hosts together that are in the same folder and site. This is
        mainly done to reduce the overhead of site communication and loading/saving of files
        """
        current_site_and_folder = None
        tasks = []

        for site_id, folder, host_name in hosts_to_discover:
            if not tasks or (site_id, folder) != current_site_and_folder or \
               len(tasks[-1].host_names) >= self._bulk_size:
                tasks.append(DiscoveryTask(site_id, folder.path(), [host_name]))
            else:
                tasks[-1].host_names.append(host_name)
            current_site_and_folder = site_id, folder
        return tasks

    def _recurse_hosts(self, folder):
        entries = []
        for host_name, host in folder.hosts().items():
            if not self._only_failed or host.discovery_failed():
                entries.append((host_name, folder))
        if self._recurse:
            for subfolder in folder.all_subfolders().values():
                entries += self._recurse_hosts(subfolder)
        return entries

    def _find_hosts_with_failed_discovery_check(self):
        # Old service name "Check_MK inventory" needs to be kept because old
        # installations may still use that name
        return sites.live().query_column("GET services\n"
                                         "Filter: description = Check_MK inventory\n"
                                         "Filter: description = Check_MK Discovery\n"
                                         "Or: 2\n"
                                         "Filter: state > 0\n"
                                         "Columns: host_name")

    def _find_hosts_with_failed_agent(self):
        return sites.live().query_column("GET services\n"
                                         "Filter: description = Check_MK\n"
                                         "Filter: state >= 2\n"
                                         "Columns: host_name")
