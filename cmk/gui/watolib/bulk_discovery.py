#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import multiprocessing as mp
import threading
import traceback
from collections.abc import Mapping, Sequence
from typing import Literal, NamedTuple, NewType, override

from pydantic import BaseModel

import cmk.ccc.resulttype as result
from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.paths import configuration_lockfile, tmp_run_dir

from cmk.automations.results import ServiceDiscoveryResult as AutomationDiscoveryResult

from cmk.checkengine.discovery import (
    DiscoveryReport,
    DiscoverySettingFlags,
    DiscoverySettings,
    DiscoveryValueSpecModel,
    TransitionCounter,
)

from cmk.gui.background_job import (
    AlreadyRunningError,
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.job_scheduler_client import StartupError
from cmk.gui.logged_in import user
from cmk.gui.utils import gen_id
from cmk.gui.utils.request_context import copy_request_context
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
                                    value=DiscoverySettingFlags(
                                        add_new_services=True,
                                        remove_vanished_services=True,
                                        update_host_labels=True,
                                        update_changed_service_labels=True,
                                        update_changed_service_parameters=True,
                                    ),
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
                                            "update_changed_service_parameters",
                                            Checkbox(
                                                label=_("Update service parameters"),
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
    param: tuple[Literal["update_everything", "custom"], Mapping[str, bool] | None],
) -> DiscoveryValueSpecModel:
    ident, flags = param
    if ident == "update_everything" or flags is None:
        # handle temporary 2.4 beta state and inconsistent 2.3 state
        return (
            "update_everything",
            DiscoverySettingFlags(
                add_new_services=True,
                remove_vanished_services=True,
                update_host_labels=True,
                update_changed_service_labels=True,
                update_changed_service_parameters=True,
            ),
        )

    return (
        "custom",
        DiscoverySettingFlags(
            add_new_services=flags["add_new_services"],
            remove_vanished_services=flags["remove_vanished_services"],
            update_host_labels=flags["update_host_labels"],
            update_changed_service_labels=flags.get("update_changed_service_labels", False),
            update_changed_service_parameters=flags.get(
                "update_changed_service_parameters",
                bool(flags.get("update_changed_service_params", False)),
            ),
        ),
    )


class _DiscoveryTaskResult(NamedTuple):
    task: DiscoveryTask
    result: AutomationDiscoveryResult | None
    error: tuple[Exception, str] | None


class BulkDiscoveryBackgroundJob(BackgroundJob):
    job_prefix = "bulk_discovery"
    lock_file = tmp_run_dir / "bulk_discovery.lock"

    @classmethod
    @override
    def gui_title(cls) -> str:
        return _("Bulk discovery")

    def __init__(self) -> None:
        job_id = f"{self.job_prefix}-{gen_id()}"
        super().__init__(job_id)

    @override
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
        *,
        pprint_value: bool,
        debug: bool,
    ) -> None:
        job_interface.send_progress_update(_("Waiting to acquire lock"))
        with job_interface.gui_context(), store.locked(self.lock_file):
            job_interface.send_progress_update(_("Acquired lock"))
            self._do_execute(
                mode,
                do_scan,
                ignore_errors,
                tasks,
                job_interface,
                pprint_value=pprint_value,
                debug=debug,
            )

    def _do_execute(
        self,
        mode: DiscoverySettings,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        tasks: Sequence[DiscoveryTask],
        job_interface: BackgroundProcessInterface,
        *,
        pprint_value: bool,
        debug: bool,
    ) -> None:
        self._initialize_statistics(
            num_hosts_total=sum(len(task.host_names) for task in tasks),
        )
        job_interface.send_progress_update(_("Bulk discovery started..."))

        tasks_by_site: dict[SiteId, list[DiscoveryTask]] = {}
        for task in tasks:
            tasks_by_site.setdefault(task.site_id, []).append(task)

        result_queue: mp.Queue[_DiscoveryTaskResult | None] = mp.Queue()
        result_processing_thread = threading.Thread(
            target=copy_request_context(self._process_discovery_results),
            args=(result_queue, len(tasks_by_site), job_interface, pprint_value),
        )

        def run(site_tasks: list[DiscoveryTask]) -> None:
            self._run_discovery_tasks(
                result_queue, site_tasks, mode, do_scan, ignore_errors, debug=debug
            )

        with mp.pool.ThreadPool(processes=len(tasks_by_site)) as task_pool:
            for site_tasks in tasks_by_site.values():
                task_pool.apply_async(func=copy_request_context(run), args=(site_tasks,))

            try:
                result_processing_thread.start()

                task_pool.close()
                task_pool.join()
            finally:
                result_processing_thread.join()

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
            _("Host labels: %d total (%d added, %d changed, %d removed, %d kept)")
            % (
                self._num_host_labels.total,
                self._num_host_labels.new,
                self._num_host_labels.changed,
                self._num_host_labels.removed,
                self._num_host_labels.kept,
            )
        )
        job_interface.send_progress_update(
            _("Services: %d total (%d added, %d changed, %d removed, %d kept)")
            % (
                self._num_services.total,
                self._num_services.new,
                self._num_services.changed,
                self._num_services.removed,
                self._num_services.kept,
            )
        )

        job_interface.send_result_message(_("Bulk discovery successful"))

    def _run_discovery_tasks(
        self,
        queue: "mp.Queue[_DiscoveryTaskResult | None]",
        site_tasks: list[DiscoveryTask],
        mode: DiscoverySettings,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        *,
        debug: bool,
    ) -> None:
        for task in site_tasks:
            try:
                result = discovery(
                    task.site_id,
                    mode,
                    task.host_names,
                    scan=do_scan,
                    raise_errors=not ignore_errors,
                    timeout=request.request_timeout - 2,
                    non_blocking_http=True,
                    debug=debug,
                )
                queue.put(
                    _DiscoveryTaskResult(
                        task,
                        result,
                        None,
                    )
                )
            except Exception as exc:
                # Needs to be formatted in this thread, since the traceback is a thread local
                # and the error handling is done in another thread.
                queue.put(_DiscoveryTaskResult(task, None, (exc, traceback.format_exc())))

        # Indicate result processing thread that we're done
        queue.put(None)

    def _initialize_statistics(self, *, num_hosts_total: int) -> None:
        self._num_hosts_total = num_hosts_total
        self._num_hosts_processed = 0
        self._num_hosts_succeeded = 0
        self._num_hosts_skipped = 0
        self._num_hosts_failed = 0
        self._num_services = TransitionCounter()
        self._num_host_labels = TransitionCounter()

    def _process_discovery_error(
        self,
        job_interface: BackgroundProcessInterface,
        task: DiscoveryTask,
        exception: tuple[Exception, str],
    ) -> None:
        self._num_hosts_failed += len(task.host_names)
        if task.site_id:
            msg = _("Error during discovery of %s on site %s") % (
                ", ".join(task.host_names),
                task.site_id,
            )
        else:
            msg = _("Error during discovery of %s") % (", ".join(task.host_names))
        self._logger.warning(f"{msg}, Error: {exception[0]}")
        job_interface.send_progress_update(f"{msg}, Error: {exception[0]}")

        # only show traceback on debug
        self._logger.debug(f"Traceback: {exception[1]}")

    def _process_discovery_results(
        self,
        results: "mp.Queue[_DiscoveryTaskResult | None]",
        n_task_threads: int,
        job_interface: BackgroundProcessInterface,
        pprint_value: bool,
    ) -> None:
        remaining_threads = n_task_threads
        while True:
            result = results.get()

            if result is None:
                remaining_threads -= 1
                if remaining_threads == 0:
                    break
                continue

            if result.error:
                self._process_discovery_error(job_interface, result.task, result.error)
            elif result.result:
                try:
                    self._process_discovery_result(
                        result.task,
                        result.result,
                        job_interface,
                        pprint_value=pprint_value,
                    )
                except Exception as exc:
                    self._process_discovery_error(
                        job_interface, result.task, (exc, traceback.format_exc())
                    )

            self._num_hosts_processed += len(result.task.host_names)

    def _process_discovery_result(
        self,
        task: DiscoveryTask,
        response: AutomationDiscoveryResult,
        job_interface: BackgroundProcessInterface,
        *,
        pprint_value: bool,
    ) -> None:
        # The following code updates the host config. The progress from loading the Setup folder
        # until it has been saved needs to be locked.
        with store.lock_checkmk_configuration(configuration_lockfile):
            tree = folder_tree()
            tree.invalidate_caches()
            folder = tree.folder(task.folder_path)
            hosts = folder.hosts()
            for count, hostname in enumerate(task.host_names, self._num_hosts_processed + 1):
                self._process_service_counts_for_host(response.hosts[hostname])
                msg = self._process_discovery_result_for_host(
                    hosts[hostname], response.hosts[hostname], pprint_value=pprint_value
                )
                job_interface.send_progress_update(
                    f"[{count}/{self._num_hosts_total}] {hostname}: {msg}"
                )

    def _process_service_counts_for_host(self, result: DiscoveryReport) -> None:
        self._num_services += result.services
        self._num_host_labels += result.host_labels

    def _process_discovery_result_for_host(
        self, host: Host, result: DiscoveryReport, *, pprint_value: bool
    ) -> str:
        if result.error_text == "":
            self._num_hosts_skipped += 1
            return _("discovery skipped: host not monitored")

        if result.error_text is not None:
            self._num_hosts_failed += 1
            if not host.locked():
                host.set_discovery_failed(pprint_value=pprint_value)
            return _("discovery failed: %s") % result.error_text

        self._num_hosts_succeeded += 1

        add_service_change(
            action_name="bulk-discovery",
            text=_(
                "Discovery on host %s: %d services (%d added, %d changed, %d removed, %d kept)"
                "and %d host labels (%d added, %d changed, %d removed, %d kept)"
            )
            % (
                host.name(),
                result.services.total,
                result.services.new,
                result.services.changed,
                result.services.removed,
                result.services.kept,
                result.host_labels.total,
                result.host_labels.new,
                result.host_labels.changed,
                result.host_labels.removed,
                result.host_labels.kept,
            ),
            user_id=user.id,
            object_ref=host.object_ref(),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            site_id=host.site_id(),
            diff_text=result.diff_text,
            use_git=active_config.wato_use_git,
        )

        if not host.locked():
            host.clear_discovery_failed(pprint_value=pprint_value)

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


def start_bulk_discovery(
    job: BulkDiscoveryBackgroundJob,
    hosts: list[DiscoveryHost],
    discovery_mode: DiscoverySettings,
    do_full_scan: DoFullScan,
    ignore_errors: IgnoreErrors,
    bulk_size: BulkSize,
    *,
    pprint_value: bool,
    debug: bool,
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
                pprint_value=pprint_value,
                debug=debug,
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
    pprint_value: bool
    debug: bool


def bulk_discovery_job_entry_point(
    job_interface: BackgroundProcessInterface, args: BulkDiscoveryJobArgs
) -> None:
    BulkDiscoveryBackgroundJob().do_execute(
        args.discovery_mode,
        args.do_full_scan,
        args.ignore_errors,
        args.tasks,
        job_interface,
        pprint_value=args.pprint_value,
        debug=args.debug,
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
