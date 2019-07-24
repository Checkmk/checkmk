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

from typing import NamedTuple, List  # pylint: disable=unused-import

import cmk.utils.store as store

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    RadioChoice,
    Tuple,
    Integer,
)

from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.automations import check_mk_automation
from cmk.gui.watolib.changes import add_service_change
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.plugins.wato import WatoBackgroundJob

DiscoveryHost = NamedTuple("DiscoveryHost", [("site_id", str), ("folder_path", str),
                                             ("host_name", str)])
DiscoveryTask = NamedTuple("DiscoveryTask", [("site_id", str), ("folder_path", str),
                                             ("host_names", list)])


def get_tasks(hosts_to_discover, bulk_size):
    # type: (List[DiscoveryHost], int) -> List[DiscoveryTask]
    """Create a list of tasks for the job

    Each task groups the hosts together that are in the same folder and site. This is
    mainly done to reduce the overhead of site communication and loading/saving of files
    """
    current_site_and_folder = None
    tasks = []  # type: List[DiscoveryTask]

    for site_id, folder_path, host_name in sorted(hosts_to_discover):
        if not tasks or (site_id, folder_path) != current_site_and_folder or \
           len(tasks[-1].host_names) >= bulk_size:
            tasks.append(DiscoveryTask(site_id, folder_path, [host_name]))
        else:
            tasks[-1].host_names.append(host_name)
        current_site_and_folder = site_id, folder_path
    return tasks


def vs_bulk_discovery(render_form=False, include_subfolders=True):
    if render_form:
        render = "form"
    else:
        render = None

    if include_subfolders:
        selection_elements = [Checkbox(label=_("Include all subfolders"), default_value=True)]
    else:
        selection_elements = []

    selection_elements += [
        Checkbox(label=_("Only include hosts that failed on previous discovery"),
                 default_value=False),
        Checkbox(label=_("Only include hosts with a failed discovery check"), default_value=False),
        Checkbox(label=_("Exclude hosts where the agent is unreachable"), default_value=False),
    ]

    return Dictionary(
        title=_("Bulk discovery"),
        render=render,
        elements=[
            ("mode",
             RadioChoice(
                 title=_("Mode"),
                 orientation="vertical",
                 default_value="new",
                 choices=[
                     ("new", _("Add unmonitored services")),
                     ("remove", _("Remove vanished services")),
                     ("fixall", _("Add unmonitored & remove vanished services")),
                     ("refresh", _("Refresh all services (tabula rasa)")),
                 ],
             )),
            ("selection", Tuple(title=_("Selection"), elements=selection_elements)),
            ("performance",
             Tuple(title=_("Performance options"),
                   elements=[
                       Checkbox(label=_("Use cached data if present"), default_value=True),
                       Checkbox(label=_("Do full SNMP scan for SNMP devices"), default_value=True),
                       Integer(label=_("Number of hosts to handle at once"), default_value=10),
                   ])),
            ("error_handling",
             Checkbox(title=_("Error handling"),
                      label=_("Ignore errors in single check plugins"),
                      default_value=True)),
        ],
        optional_keys=[],
    )


# TODO: This job should be executable multiple times at once
@gui_background_job.job_registry.register
class BulkDiscoveryBackgroundJob(WatoBackgroundJob):
    job_prefix = "bulk_discovery"

    @classmethod
    def gui_title(cls):
        return _("Bulk Discovery")

    def __init__(self):
        kwargs = {}
        kwargs["title"] = self.gui_title()
        kwargs["lock_wato"] = False
        kwargs["deletable"] = False
        kwargs["stoppable"] = False

        super(BulkDiscoveryBackgroundJob, self).__init__(self.job_prefix, **kwargs)

    def _back_url(self):
        return Folder.current().url()

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

        counts, failed_hosts = check_mk_automation(task.site_id,
                                                   "inventory",
                                                   arguments,
                                                   timeout=timeout)

        return counts, failed_hosts

    def _process_discovery_results(self, task, job_interface, counts, failed_hosts):
        # The following code updates the host config. The progress from loading the WATO folder
        # until it has been saved needs to be locked.
        with store.lock_checkmk_configuration():
            Folder.invalidate_caches()
            folder = Folder.folder(task.folder_path)
            for hostname in task.host_names:
                self._process_service_counts_for_host(counts[hostname])
                msg = self._process_discovery_result_for_host(folder.host(hostname),
                                                              failed_hosts.get(hostname, False),
                                                              counts[hostname])
                job_interface.send_progress_update("%s: %s" % (hostname, msg))

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

        add_service_change(
            host, "bulk-discovery",
            _("Did service discovery on host %s: %d added, %d removed, %d kept, "
              "%d total services") % tuple([host.name()] + host_counts))

        if not host.locked():
            host.clear_discovery_failed()

        return _("discovery successful")
