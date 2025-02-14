#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NamedTuple, NewType, TypedDict

from pydantic import BaseModel

from livestatus import SiteId

from cmk.ccc import store

import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostName
from cmk.utils.paths import configuration_lockfile

from cmk.automations.results import ServiceDiscoveryResult as AutomationDiscoveryResult

from cmk.checkengine.discovery import DiscoveryResult, DiscoverySettings

from cmk.gui.background_job import (
    AlreadyRunningError,
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
    StartupError,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    Dictionary,
    FixedValue,
    Integer,
    Migrate,
    Tuple,
    ValueSpec,
)
from cmk.gui.watolib.changes import add_service_change
from cmk.gui.watolib.check_mk_automations import discovery
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    generate_hosts_to_update_settings,
)
from cmk.gui.watolib.config_domain_name import (
    CORE as CORE_DOMAIN,
)
from cmk.gui.watolib.hosts_and_folders import disk_or_search_folder_from_request, folder_tree, Host

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


def vs_bulk_discovery(render_form: bool = False, include_subfolders: bool = True) -> Dictionary:
    selection_elements: list[ValueSpec] = []

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
                Migrate(
                    migrate=_migrate_automatic_rediscover_parameters,
                    valuespec=CascadingDropdown(
                        title=_("Parameters"),
                        sorted=False,
                        choices=[
                            (
                                "update_everything",
                                _("Refresh all services and host labels (tabula rasa)"),
                                FixedValue(
                                    value=None,
                                    title=_("Refresh all services and host labels (tabula rasa)"),
                                    totext="",
                                ),
                            ),
                            (
                                "custom",
                                _("Custom service configuration update"),
                                Dictionary(
                                    elements=[
                                        (
                                            "add_new_services",
                                            Checkbox(
                                                label=_("Monitor undecided services"),
                                                default_value=False,
                                            ),
                                        ),
                                        (
                                            "remove_vanished_services",
                                            Checkbox(
                                                label=_("Remove vanished services"),
                                                default_value=False,
                                            ),
                                        ),
                                        (
                                            "update_changed_service_labels",
                                            Checkbox(
                                                label=_("Update service labels"),
                                                default_value=False,
                                            ),
                                        ),
                                        (
                                            "update_host_labels",
                                            Checkbox(
                                                label=_("Update host labels"),
                                                default_value=False,
                                            ),
                                        ),
                                    ],
                                    optional_keys=[],
                                    indent=False,
                                ),
                            ),
                        ],
                    ),
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
                    label=_("Ignore errors in single check plug-ins"),
                    default_value=True,
                ),
            ),
        ],
        optional_keys=[],
    )


def _migrate_automatic_rediscover_parameters(
    param: str | tuple[str, dict[str, bool]],
) -> tuple[str, dict[str, bool]]:
    # already migrated
    if isinstance(param, tuple):
        return param

    if param == "new":
        return (
            "custom",
            {
                "add_new_services": True,
                "remove_vanished_services": False,
                "update_host_labels": True,
            },
        )

    if param == "remove":
        return (
            "custom",
            {
                "add_new_services": False,
                "remove_vanished_services": True,
                "update_host_labels": False,
            },
        )

    if param == "fixall":
        return (
            "custom",
            {
                "add_new_services": True,
                "remove_vanished_services": True,
                "update_host_labels": True,
            },
        )

    if param == "refresh":
        return (
            "update_everything",
            {
                "add_new_services": True,
                "remove_vanished_services": True,
                "update_host_labels": True,
            },
        )

    raise MKUserError(None, _("Automatic rediscovery parameter {param} not implemented"))


class BulkDiscoveryBackgroundJob(BackgroundJob):
    job_prefix = "bulk_discovery"

    @classmethod
    def gui_title(cls) -> str:
        return _("Bulk Discovery")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def _back_url(self) -> str:
        return disk_or_search_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        ).url()

    def do_execute(
        self,
        mode: DiscoverySettings,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        tasks: Sequence[DiscoveryTask],
        job_interface: BackgroundProcessInterface,
    ) -> None:
        with job_interface.gui_context():
            self._do_execute(mode, do_scan, ignore_errors, tasks, job_interface)

    def _do_execute(
        self,
        mode: DiscoverySettings,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        tasks: Sequence[DiscoveryTask],
        job_interface: BackgroundProcessInterface,
    ) -> None:
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

    def _initialize_statistics(self, *, num_hosts_total: int) -> None:
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
        mode: DiscoverySettings,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        job_interface: BackgroundProcessInterface,
    ) -> None:
        try:
            response = discovery(
                task.site_id,
                mode.to_json(),
                task.host_names,
                scan=do_scan,
                raise_errors=not ignore_errors,
                timeout=request.request_timeout - 2,
                non_blocking_http=True,
            )
            self._process_discovery_results(task, job_interface, response)
        except Exception as e:
            self._num_hosts_failed += len(task.host_names)
            if task.site_id:
                msg = _("Error during discovery of %s on site %s") % (
                    ", ".join(task.host_names),
                    task.site_id,
                )
            else:
                msg = _("Error during discovery of %s") % (", ".join(task.host_names))
            self._logger.warning(f"{msg}, Error: {e}")

            # only show traceback on debug
            self._logger.debug("Exception", exc_info=True)

        self._num_hosts_processed += len(task.host_names)

    def _process_discovery_results(
        self,
        task: DiscoveryTask,
        job_interface: BackgroundProcessInterface,
        response: AutomationDiscoveryResult,
    ) -> None:
        # The following code updates the host config. The progress from loading the Setup folder
        # until it has been saved needs to be locked.
        with store.lock_checkmk_configuration(configuration_lockfile):
            tree = folder_tree()
            tree.invalidate_caches()
            folder = tree.folder(task.folder_path)
            for count, hostname in enumerate(task.host_names, self._num_hosts_processed + 1):
                self._process_service_counts_for_host(response.hosts[hostname])
                msg = self._process_discovery_result_for_host(
                    folder.load_host(hostname), response.hosts[hostname]
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

    def _process_discovery_result_for_host(self, host: Host, result: DiscoveryResult) -> str:
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
            host.object_ref(),
            [config_domain_registry[CORE_DOMAIN]],
            {CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            host.site_id(),
            diff_text=result.diff_text,
        )

        if not host.locked():
            host.clear_discovery_failed()

        return _("discovery successful")


def prepare_hosts_for_discovery(hostnames: Sequence[str]) -> list[DiscoveryHost]:
    hosts_to_discover = []
    for host_name in hostnames:
        host = Host.host(HostName(host_name))
        if host is None:
            raise MKUserError(None, _("The host '%s' does not exist") % host_name)
        host.permissions.need_permission("write")
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
        job_state=status.state,
        logs=JobLogs(
            result=status.loginfo["JobResult"],
            progress=status.loginfo["JobProgressUpdate"],
        ),
    )


def start_bulk_discovery(
    job: BulkDiscoveryBackgroundJob,
    hosts: list[DiscoveryHost],
    discovery_mode: DiscoverySettings,
    do_full_scan: DoFullScan,
    ignore_errors: IgnoreErrors,
    bulk_size: BulkSize,
) -> result.Result[None, AlreadyRunningError | StartupError]:
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
    return job.start(
        JobTarget(
            callable=bulk_discovery_job_entry_point,
            args=BulkDiscoveryJobArgs(
                discovery_mode=discovery_mode,
                do_full_scan=do_full_scan,
                ignore_errors=ignore_errors,
                tasks=tasks,
            ),
        ),
        InitialStatusArgs(
            title=job.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )


class BulkDiscoveryJobArgs(BaseModel, frozen=True):
    discovery_mode: DiscoverySettings
    do_full_scan: DoFullScan
    ignore_errors: IgnoreErrors
    tasks: Sequence[DiscoveryTask]


def bulk_discovery_job_entry_point(
    job_interface: BackgroundProcessInterface, args: BulkDiscoveryJobArgs
) -> None:
    BulkDiscoveryBackgroundJob().do_execute(
        args.discovery_mode, args.do_full_scan, args.ignore_errors, args.tasks, job_interface
    )


def _create_tasks_from_hosts(
    hosts_to_discover: list[DiscoveryHost], bulk_size: BulkSize
) -> list[DiscoveryTask]:
    """Create a list of tasks for the job

    Each task groups the hosts together that are in the same folder and site. This is
    mainly done to reduce the overhead of site communication and loading/saving of files
    """
    current_site_and_folder = None
    tasks: list[DiscoveryTask] = []

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
