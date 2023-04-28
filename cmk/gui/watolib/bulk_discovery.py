#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, MutableSequence, NamedTuple, NewType, Sequence, TypedDict

from livestatus import SiteId

import cmk.utils.store as store
from cmk.utils.type_defs import DiscoveryResult

from cmk.automations.results import DiscoveryResult as AutomationDiscoveryResult

import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.valuespec import Checkbox, Dictionary, DropdownChoice, Integer, Tuple, ValueSpec
from cmk.gui.watolib.changes import add_service_change
from cmk.gui.watolib.check_mk_automations import discovery
from cmk.gui.watolib.hosts_and_folders import Folder, Host
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

DiscoveryMode = NewType("DiscoveryMode", str)
DoFullScan = NewType("DoFullScan", bool)

BulkSize = NewType("BulkSize", int)
IgnoreErrors = NewType("IgnoreErrors", bool)


class DiscoveryHost(NamedTuple):
    site_id: str
    folder_path: str
    host_name: str


class DiscoveryTask(NamedTuple):
    site_id: SiteId
    folder_path: str
    host_names: list


def vs_bulk_discovery(render_form=False, include_subfolders=True):
    selection_elements: List[ValueSpec] = []

    if include_subfolders:
        selection_elements.append(Checkbox(label=_("Include all subfolders"), default_value=True))

    selection_elements += [
        Checkbox(
            label=_("Only include hosts that failed on previous discovery"), default_value=False
        ),
        Checkbox(label=_("Only include hosts with a failed discovery check"), default_value=False),
        Checkbox(label=_("Exclude hosts where the agent is unreachable"), default_value=False),
    ]

    return Dictionary(
        title=_("Bulk discovery"),
        render="form" if render_form else "normal",
        elements=[
            (
                "mode",
                DropdownChoice(
                    title=_("Mode"),
                    default_value="new",
                    choices=[
                        ("new", _("Add unmonitored services and new host labels")),
                        ("remove", _("Remove vanished services")),
                        (
                            "fixall",
                            _(
                                "Add unmonitored services and new host labels, remove vanished services"
                            ),
                        ),
                        ("refresh", _("Refresh all services (tabula rasa), add new host labels")),
                        ("only-host-labels", _("Only discover new host labels")),
                    ],
                ),
            ),
            ("selection", Tuple(title=_("Selection"), elements=selection_elements)),
            (
                "performance",
                Tuple(
                    title=_("Performance options"),
                    elements=[
                        Checkbox(label=_("Do a full service scan"), default_value=True),
                        Integer(label=_("Number of hosts to handle at once"), default_value=10),
                    ],
                ),
            ),
            (
                "error_handling",
                Checkbox(
                    title=_("Error handling"),
                    label=_("Ignore errors in single check plugins"),
                    default_value=True,
                ),
            ),
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
        super().__init__(
            self.job_prefix,
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def _back_url(self):
        return Folder.current().url()

    def do_execute(
        self,
        mode: DiscoveryMode,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        tasks: Sequence[DiscoveryTask],
        job_interface=None,
    ):
        self._initialize_statistics(
            num_hosts_total=sum(len(task.host_names) for task in tasks),
        )
        job_interface.send_progress_update(_("Bulk discovery started..."))

        for task in tasks:
            self._bulk_discover_item(task, mode, do_scan, ignore_errors, job_interface)

        job_interface.send_progress_update(_("Bulk discovery finished."))

        job_interface.send_progress_update(
            _("Hosts: %d total (%d succeeded, %d skipped, %d failed)")
            % (
                self._num_hosts_total,
                self._num_hosts_succeeded,
                self._num_hosts_skipped,
                self._num_hosts_failed,
            )
        )
        job_interface.send_progress_update(
            _("Host labels: %d total (%d added)")
            % (self._num_host_labels_total, self._num_host_labels_added)
        )
        job_interface.send_progress_update(
            _("Services: %d total (%d added, %d removed, %d kept)")
            % (
                self._num_services_total,
                self._num_services_added,
                self._num_services_removed,
                self._num_services_kept,
            )
        )

        job_interface.send_result_message(_("Bulk discovery successful"))

    def _initialize_statistics(self, *, num_hosts_total: int):
        self._num_hosts_total = num_hosts_total
        self._num_hosts_processed = 0
        self._num_hosts_succeeded = 0
        self._num_hosts_skipped = 0
        self._num_hosts_failed = 0
        self._num_services_added = 0
        self._num_services_removed = 0
        self._num_services_kept = 0
        self._num_services_total = 0
        self._num_host_labels_total = 0
        self._num_host_labels_added = 0

    def _bulk_discover_item(
        self,
        task: DiscoveryTask,
        mode: DiscoveryMode,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        job_interface,
    ):

        try:
            response = self._execute_discovery(task, mode, do_scan, ignore_errors)
            self._process_discovery_results(task, job_interface, response)
        except Exception:
            self._num_hosts_failed += len(task.host_names)
            if task.site_id:
                msg = _("Error during discovery of %s on site %s") % (
                    ", ".join(task.host_names),
                    task.site_id,
                )
            else:
                msg = _("Error during discovery of %s") % (", ".join(task.host_names))
            self._logger.exception(msg)

        self._num_hosts_processed += len(task.host_names)

    def _execute_discovery(
        self,
        task: DiscoveryTask,
        mode: DiscoveryMode,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
    ) -> AutomationDiscoveryResult:
        flags: MutableSequence[str] = []
        if not ignore_errors:
            flags.append("@raiseerrors")
        if do_scan:
            flags.append("@scan")

        return discovery(
            task.site_id,
            mode,
            flags,
            task.host_names,
            timeout=request.request_timeout - 2,
            non_blocking_http=True,
        )

    def _process_discovery_results(
        self,
        task: DiscoveryTask,
        job_interface,
        response: AutomationDiscoveryResult,
    ) -> None:
        # The following code updates the host config. The progress from loading the WATO folder
        # until it has been saved needs to be locked.
        with store.lock_checkmk_configuration():
            Folder.invalidate_caches()
            folder = Folder.folder(task.folder_path)
            for count, hostname in enumerate(task.host_names, self._num_hosts_processed + 1):
                self._process_service_counts_for_host(response.hosts[hostname])
                msg = self._process_discovery_result_for_host(
                    folder.host(hostname), response.hosts[hostname]
                )
                job_interface.send_progress_update(
                    f"[{count}/{self._num_hosts_total}] {hostname}: {msg}"
                )

    def _process_service_counts_for_host(self, result: DiscoveryResult) -> None:
        self._num_services_added += result.self_new
        self._num_services_removed += result.self_removed
        self._num_services_kept += result.self_kept
        self._num_services_total += result.self_total
        self._num_host_labels_added += result.self_new_host_labels
        self._num_host_labels_total += result.self_total_host_labels

    def _process_discovery_result_for_host(self, host, result: DiscoveryResult) -> str:
        if result.error_text == "":
            self._num_hosts_skipped += 1
            return _("discovery skipped: host not monitored")

        if result.error_text is not None:
            self._num_hosts_failed += 1
            if not host.locked():
                host.set_discovery_failed()
            return _("discovery failed: %s") % result.error_text

        self._num_hosts_succeeded += 1

        add_service_change(
            host,
            "bulk-discovery",
            _(
                "Did service discovery on host %s: %d added, %d removed, %d kept, "
                "%d total services and %d host labels added, %d host labels total"
            )
            % (
                host.name(),
                result.self_new,
                result.self_removed,
                result.self_kept,
                result.self_total,
                result.self_new_host_labels,
                result.self_total_host_labels,
            ),
            diff_text=result.diff_text,
        )

        if not host.locked():
            host.clear_discovery_failed()

        return _("discovery successful")


def prepare_hosts_for_discovery(hostnames: Sequence[str]) -> List[DiscoveryHost]:
    hosts_to_discover = []
    for host_name in hostnames:
        host = Host.host(host_name)
        if host is None:
            raise MKUserError(None, _("The host '%s' does not exist") % host_name)
        host.need_permission("write")
        hosts_to_discover.append(DiscoveryHost(host.site_id(), host.folder().path(), host_name))
    return hosts_to_discover


class JobLogs(TypedDict):
    result: Sequence[str]
    progress: Sequence[str]


class BulkDiscoveryStatus(TypedDict):
    is_active: bool
    job_state: str
    logs: JobLogs


def bulk_discovery_job_status(job: BulkDiscoveryBackgroundJob) -> BulkDiscoveryStatus:
    status = job.get_status()
    return BulkDiscoveryStatus(
        is_active=job.is_active(),
        job_state=status["state"],
        logs=JobLogs(
            result=status["loginfo"]["JobResult"],
            progress=status["loginfo"]["JobProgressUpdate"],
        ),
    )


def start_bulk_discovery(
    job: BulkDiscoveryBackgroundJob,
    hosts: List[DiscoveryHost],
    discovery_mode: DiscoveryMode,
    do_full_scan: DoFullScan,
    ignore_errors: IgnoreErrors,
    bulk_size: BulkSize,
) -> None:
    """Start a bulk discovery job with the given options

    Args:
        job:
            The BackgroundJob to use to start the bulk discovery

        hosts:
            Sequence of hosts to perform the discovery on

        discovery_mode:
            * `new` - Add unmonitored services and new host labels
            * `remove` - Remove vanished services
            * `fix_all` - Add unmonitored services and new host labels, remove vanished services
            * `refresh` - Refresh all services (tabula rasa), add new host labels
            * `only_host_labels` - Only discover new host labels

        do_full_scan:
            Boolean indicating whether to do a full scan

        ignore_errors:
            Boolean indicating whether to ignore errors or not

        bulk_size:
            The number of hosts to handle at once

    """
    tasks = _create_tasks_from_hosts(hosts, bulk_size)
    job.set_function(job.do_execute, discovery_mode, do_full_scan, ignore_errors, tasks)
    job.start()


def _create_tasks_from_hosts(
    hosts_to_discover: List[DiscoveryHost], bulk_size: BulkSize
) -> List[DiscoveryTask]:
    """Create a list of tasks for the job

    Each task groups the hosts together that are in the same folder and site. This is
    mainly done to reduce the overhead of site communication and loading/saving of files
    """
    current_site_and_folder = None
    tasks: List[DiscoveryTask] = []

    for site_id, folder_path, host_name in sorted(hosts_to_discover):
        if (
            not tasks
            or (site_id, folder_path) != current_site_and_folder
            or len(tasks[-1].host_names) >= bulk_size
        ):
            tasks.append(DiscoveryTask(SiteId(site_id), folder_path, [host_name]))
        else:
            tasks[-1].host_names.append(host_name)
        current_site_and_folder = site_id, folder_path
    return tasks
