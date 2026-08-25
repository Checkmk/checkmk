#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="type-arg"

import multiprocessing as mp
import threading
import traceback
from collections.abc import Mapping, Sequence
from typing import Literal, NamedTuple, NewType, override

from pydantic import BaseModel

import cmk.ccc.resulttype as result
from cmk.automations.results import ServiceDiscoveryResult as AutomationDiscoveryResult
from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.checkengine.discovery import (
    DiscoveryReport,
    DiscoverySettingFlags,
    DiscoverySettings,
    DiscoveryValueSpecModel,
    TransitionCounter,
)
from cmk.gui.background_job.job import (
    AlreadyRunningError,
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.form_specs.unstable.legacy_converter import Tuple as FSTuple
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.job_scheduler_client import StartupError
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import AnnotatedUserId
from cmk.gui.utils.misc import gen_id
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
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
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.automations import (
    make_automation_config,
)
from cmk.gui.watolib.check_mk_automations import discovery
from cmk.gui.watolib.config_domain_name import (
    CORE as CORE_DOMAIN,
)
from cmk.gui.watolib.config_domain_name import (
    generate_hosts_to_update_settings,
)
from cmk.gui.watolib.hosts_and_folders import (
    disk_or_search_folder_from_request,
    folder_tree,
    FolderTree,
    Host,
)
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Label, Title
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.paths import configuration_lockfile, tmp_run_dir

DoFullScan = NewType("DoFullScan", bool)

BulkSize = NewType("BulkSize", int)
IgnoreErrors = NewType("IgnoreErrors", bool)


class DiscoveryHost(NamedTuple):
    site_id: str
    automation_config: LocalAutomationConfig | RemoteAutomationConfig
    folder_path: str
    host_name: str


class DiscoveryTask(NamedTuple):
    site_id: SiteId
    automation_config: LocalAutomationConfig | RemoteAutomationConfig
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


_UPDATE_EVERYTHING_FLAGS = DiscoverySettingFlags(
    add_new_services=True,
    remove_vanished_services=True,
    update_host_labels=True,
    update_changed_service_labels=True,
    update_changed_service_parameters=True,
)


def _fs_bulk_discovery_mode() -> TransformDataForLegacyFormatOrRecomposeFunction:
    """The stored format is (ident, flags) for both idents, but the
    "update_everything" flags are not editable, so the form only carries the
    ident there and the flags are restored on the way back to disk."""

    def from_disk(value: object) -> tuple[str, object]:
        ident, flags = _migrate_automatic_rediscover_parameters(value)  # type: ignore[arg-type]
        return (ident, True) if ident == "update_everything" else (ident, flags)

    def to_disk(value: object) -> tuple[str, DiscoverySettingFlags]:
        assert isinstance(value, tuple)
        ident, flags = value
        if ident == "update_everything":
            return ident, _UPDATE_EVERYTHING_FLAGS
        return ident, flags

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=fs.CascadingSingleChoice(
            title=Title("Parameters"),
            prefill=fs.DefaultValue("update_everything"),
            elements=[
                fs.CascadingSingleChoiceElement(
                    name="update_everything",
                    title=Title("Refresh all services and host labels (tabula rasa)"),
                    parameter_form=fs.FixedValue(value=True, label=Label("")),
                ),
                fs.CascadingSingleChoiceElement(
                    name="custom",
                    title=Title("Custom service configuration update"),
                    parameter_form=fs.Dictionary(
                        elements={
                            "add_new_services": fs.DictElement(
                                required=True,
                                parameter_form=fs.BooleanChoice(
                                    label=Label("Monitor undecided services"),
                                    prefill=fs.DefaultValue(False),
                                ),
                            ),
                            "remove_vanished_services": fs.DictElement(
                                required=True,
                                parameter_form=fs.BooleanChoice(
                                    label=Label("Remove vanished services"),
                                    prefill=fs.DefaultValue(False),
                                ),
                            ),
                            "update_changed_service_labels": fs.DictElement(
                                required=True,
                                parameter_form=fs.BooleanChoice(
                                    label=Label("Update service labels"),
                                    prefill=fs.DefaultValue(False),
                                ),
                            ),
                            "update_changed_service_parameters": fs.DictElement(
                                required=True,
                                parameter_form=fs.BooleanChoice(
                                    label=Label("Update service parameters"),
                                    prefill=fs.DefaultValue(False),
                                ),
                            ),
                            "update_host_labels": fs.DictElement(
                                required=True,
                                parameter_form=fs.BooleanChoice(
                                    label=Label("Update host labels"),
                                    prefill=fs.DefaultValue(False),
                                ),
                            ),
                        },
                    ),
                ),
            ],
        ),
        from_disk=from_disk,
        to_disk=to_disk,
    )


def fs_bulk_discovery() -> fs.Dictionary:
    """FormSpec counterpart of vs_bulk_discovery() for the global setting.

    The bulk discovery page still uses the valuespec, so both have to produce
    the same stored format."""
    return fs.Dictionary(
        title=Title("Bulk discovery"),
        elements={
            "mode": fs.DictElement(required=True, parameter_form=_fs_bulk_discovery_mode()),
            "selection": fs.DictElement(
                required=True,
                parameter_form=FSTuple(
                    title=Title("Selection"),
                    elements=[
                        fs.BooleanChoice(
                            label=Label("Include all subfolders"),
                            prefill=fs.DefaultValue(True),
                        ),
                        fs.BooleanChoice(
                            label=Label("Only include hosts that failed on previous discovery"),
                            prefill=fs.DefaultValue(False),
                        ),
                        fs.BooleanChoice(
                            label=Label("Only include hosts with a failed discovery check"),
                            prefill=fs.DefaultValue(False),
                        ),
                        fs.BooleanChoice(
                            label=Label("Exclude hosts where the agent is unreachable"),
                            prefill=fs.DefaultValue(False),
                        ),
                    ],
                ),
            ),
            "performance": fs.DictElement(
                required=True,
                parameter_form=FSTuple(
                    title=Title("Performance options"),
                    elements=[
                        fs.BooleanChoice(
                            label=Label("Do a full service scan"),
                            prefill=fs.DefaultValue(True),
                        ),
                        fs.Integer(
                            label=Label("Number of hosts to handle at once"),
                            prefill=fs.DefaultValue(10),
                        ),
                    ],
                ),
            ),
            "error_handling": fs.DictElement(
                required=True,
                parameter_form=fs.BooleanChoice(
                    title=Title("Error handling"),
                    label=Label("Ignore errors in single check plug-ins"),
                    prefill=fs.DefaultValue(True),
                ),
            ),
        },
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
            folder_tree(),
            request.var("folder"),
            request.get_ascii_input("host"),
            acting_user=user,
            request=request,
        ).url(request)

    def do_execute(
        self,
        mode: DiscoverySettings,
        do_scan: DoFullScan,
        ignore_errors: IgnoreErrors,
        tasks: Sequence[DiscoveryTask],
        job_interface: BackgroundProcessInterface,
        user_permission_config: UserPermissionSerializableConfig,
        *,
        pprint_value: bool,
        debug: bool,
        use_git: bool,
        activation_site_configs: SiteConfigurations,
        local_site: SiteId,
        acting_user: UserId | None,
    ) -> None:
        if not tasks:
            job_interface.send_result_message(
                _("The selected options do not match any hosts, nothing to do.")
            )
            return
        job_interface.send_progress_update(_("Waiting to acquire lock"))
        with (
            job_interface.gui_context(
                UserPermissions.from_serialized_config(user_permission_config, permission_registry)
            ),
            store.locked(self.lock_file),
        ):
            job_interface.send_progress_update(_("Acquired lock"))
            self._do_execute(
                mode,
                do_scan,
                ignore_errors,
                tasks,
                job_interface,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                activation_site_configs=activation_site_configs,
                local_site=local_site,
                acting_user=acting_user,
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
        use_git: bool,
        activation_site_configs: SiteConfigurations,
        local_site: SiteId,
        acting_user: UserId | None,
    ) -> None:
        self._initialize_statistics(
            num_hosts_total=sum(len(task.host_names) for task in tasks),
        )
        job_interface.send_progress_update(_("Bulk discovery started..."))

        tasks_by_site: dict[SiteId, list[DiscoveryTask]] = {}
        for task in tasks:
            tasks_by_site.setdefault(task.site_id, []).append(task)

        pending_changes = PendingChanges(
            activation_sites=activation_site_configs,
            local_site=local_site,
            acting_user=acting_user,
            store=PendingChangesStore(),
            hooks=(
                make_audit_log_change_hook(use_git=use_git),
                index_update_change_hook,
            ),
        )

        result_queue: mp.Queue[_DiscoveryTaskResult | None] = mp.Queue()
        result_processing_thread = threading.Thread(
            target=copy_request_context(self._process_discovery_results),
            args=(result_queue, len(tasks_by_site), job_interface, pprint_value, pending_changes),
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
            _(
                "Hosts: %(total)d total (%(succeeded)d succeeded, %(skipped)d skipped, %(failed)d failed)"
            )
            % {
                "total": self._num_hosts_total,
                "succeeded": self._num_hosts_succeeded,
                "skipped": self._num_hosts_skipped,
                "failed": self._num_hosts_failed,
            }
        )
        job_interface.send_progress_update(
            _(
                "Host labels: %(total)d total (%(added)d added, %(changed)d changed, %(removed)d removed, %(kept)d kept)"
            )
            % {
                "total": self._num_host_labels.total,
                "added": self._num_host_labels.new,
                "changed": self._num_host_labels.changed,
                "removed": self._num_host_labels.removed,
                "kept": self._num_host_labels.kept,
            }
        )
        job_interface.send_progress_update(
            _(
                "Services: %(total)d total (%(added)d added, %(changed)d changed, %(removed)d removed, %(kept)d kept)"
            )
            % {
                "total": self._num_services.total,
                "added": self._num_services.new,
                "changed": self._num_services.changed,
                "removed": self._num_services.removed,
                "kept": self._num_services.kept,
            }
        )

        job_interface.send_result_message(_("Bulk discovery successful"))

    def _run_discovery_tasks(
        self,
        queue: mp.Queue[_DiscoveryTaskResult | None],
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
                    task.automation_config,
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
            msg = _("Error during discovery of %(host_names)s on site %(site_id)s") % {
                "host_names": ", ".join(task.host_names),
                "site_id": task.site_id,
            }
        else:
            msg = _("Error during discovery of %(host_names)s") % {
                "host_names": ", ".join(task.host_names)
            }
        self._logger.warning("%(msg)s, Error: %(error)s", {"msg": msg, "error": exception[0]})
        job_interface.send_progress_update(f"{msg}, Error: {exception[0]}")

        # only show traceback on debug
        self._logger.debug("Traceback: %(traceback)s", {"traceback": exception[1]})

    def _process_discovery_results(
        self,
        results: mp.Queue[_DiscoveryTaskResult | None],
        n_task_threads: int,
        job_interface: BackgroundProcessInterface,
        pprint_value: bool,
        pending_changes: PendingChanges,
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
                        pending_changes=pending_changes,
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
        pending_changes: PendingChanges,
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
                    hosts[hostname],
                    response.hosts[hostname],
                    pprint_value=pprint_value,
                    pending_changes=pending_changes,
                )
                job_interface.send_progress_update(
                    f"[{count}/{self._num_hosts_total}] {hostname}: {msg}"
                )

    def _process_service_counts_for_host(self, result: DiscoveryReport) -> None:
        self._num_services += result.services
        self._num_host_labels += result.host_labels

    def _process_discovery_result_for_host(
        self,
        host: Host,
        result: DiscoveryReport,
        *,
        pprint_value: bool,
        pending_changes: PendingChanges,
    ) -> str:
        if result.error_text == "":
            self._num_hosts_skipped += 1
            return _("discovery skipped: host not monitored")

        if result.error_text is not None:
            self._num_hosts_failed += 1
            if not host.locked():
                host.set_discovery_failed(pprint_value=pprint_value, acting_user=user)
            return _("discovery failed: %(error_text)s") % {"error_text": result.error_text}

        self._num_hosts_succeeded += 1

        pending_changes.add(
            Change(
                action_name="bulk-discovery",
                text=_(
                    "Discovery on host %(host)s: %(services_total)d services (%(services_added)d added, %(services_changed)d changed, %(services_removed)d removed, %(services_kept)d kept)"
                    "and %(labels_total)d host labels (%(labels_added)d added, %(labels_changed)d changed, %(labels_removed)d removed, %(labels_kept)d kept)"
                )
                % {
                    "host": host.name(),
                    "services_total": result.services.total,
                    "services_added": result.services.new,
                    "services_changed": result.services.changed,
                    "services_removed": result.services.removed,
                    "services_kept": result.services.kept,
                    "labels_total": result.host_labels.total,
                    "labels_added": result.host_labels.new,
                    "labels_changed": result.host_labels.changed,
                    "labels_removed": result.host_labels.removed,
                    "labels_kept": result.host_labels.kept,
                },
                object_ref=host.object_ref(),
                diff_text=result.diff_text,
                domains=[CORE_DOMAIN],
                domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            ),
            ChangeScope.sites([host.site_id()]),
        )

        if not host.locked():
            host.clear_discovery_failed(pprint_value=pprint_value, acting_user=user)

        return _("discovery successful")


def prepare_hosts_for_discovery(
    tree: FolderTree, hostnames: Sequence[str], site_configs: SiteConfigurations
) -> list[DiscoveryHost]:
    hosts_to_discover = []
    for host_name in hostnames:
        host = tree.host(HostName(host_name))
        if host is None:
            raise MKUserError(
                None, _("The host '%(host_name)s' does not exist") % {"host_name": host_name}
            )
        host.permissions.need_permission("write", user)
        hosts_to_discover.append(
            DiscoveryHost(
                site_id := host.site_id(),
                make_automation_config(site_configs[site_id]),
                host.folder().path(),
                host_name,
            )
        )
    return hosts_to_discover


def start_bulk_discovery(
    job: BulkDiscoveryBackgroundJob,
    hosts: list[DiscoveryHost],
    discovery_mode: DiscoverySettings,
    do_full_scan: DoFullScan,
    ignore_errors: IgnoreErrors,
    bulk_size: BulkSize,
    user_permission_config: UserPermissionSerializableConfig,
    *,
    pprint_value: bool,
    debug: bool,
    use_git: bool,
    activation_site_configs: SiteConfigurations,
    local_site: SiteId,
    acting_user: UserId | None,
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
                user_permission_config=user_permission_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
                activation_site_configs=activation_site_configs,
                local_site=local_site,
                acting_user=acting_user,
            ),
        ),
        InitialStatusArgs(
            title=job.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(acting_user) if acting_user else None,
        ),
    )


class BulkDiscoveryJobArgs(BaseModel, frozen=True):
    discovery_mode: DiscoverySettings
    do_full_scan: DoFullScan
    ignore_errors: IgnoreErrors
    tasks: Sequence[DiscoveryTask]
    user_permission_config: UserPermissionSerializableConfig
    pprint_value: bool
    debug: bool
    use_git: bool
    activation_site_configs: SiteConfigurations
    local_site: SiteId
    acting_user: AnnotatedUserId | None


def bulk_discovery_job_entry_point(
    job_interface: BackgroundProcessInterface, args: BulkDiscoveryJobArgs
) -> None:
    BulkDiscoveryBackgroundJob().do_execute(
        args.discovery_mode,
        args.do_full_scan,
        args.ignore_errors,
        args.tasks,
        job_interface,
        user_permission_config=args.user_permission_config,
        pprint_value=args.pprint_value,
        debug=args.debug,
        use_git=args.use_git,
        activation_site_configs=args.activation_site_configs,
        local_site=args.local_site,
        acting_user=args.acting_user,
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

    for site_id, automation_config, folder_path, host_name in sorted(hosts_to_discover):
        if (
            not tasks
            or (site_id, folder_path) != current_site_and_folder
            or len(tasks[-1].host_names) >= bulk_size
        ):
            tasks.append(
                DiscoveryTask(
                    SiteId(site_id),
                    automation_config,
                    folder_path,
                    [host_name],
                )
            )
        else:
            tasks[-1].host_names.append(host_name)
        current_site_and_folder = site_id, folder_path
    return tasks
