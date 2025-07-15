#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from livestatus import SiteConfiguration

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.resulttype import Result
from cmk.ccc.site import SiteId

from cmk.utils.paths import configuration_lockfile

from cmk.automations.results import Gateway, GatewayResult

from cmk.gui.background_job import (
    AlreadyRunningError,
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.job_scheduler_client import StartupError
from cmk.gui.logged_in import user
from cmk.gui.watolib import bakery
from cmk.gui.watolib.automations import (
    AnnotatedHostName,
    LocalAutomationConfig,
    make_automation_config,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.check_mk_automations import scan_parents
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import (
    disk_or_search_base_folder_from_request,
    disk_or_search_folder_from_request,
    Folder,
    folder_tree,
    Host,
)


@dataclass(frozen=True)
class ParentScanTask:
    site_id: SiteId
    automation_config: LocalAutomationConfig | RemoteAutomationConfig
    host_folder_path: str
    host_name: AnnotatedHostName


# 'nowhere'     -> no new hosts are created
# 'here'        -> new hosts are created directly in the current folder
# 'subfolder'   -> new hosts are created in a "parents" subfolder of the current folder
# 'there'       -> new hosts are created in the same folder as the host
WhereChoices = Literal["nowhere", "here", "subfolder", "there", "gateway_folder"]


@dataclass(frozen=True)
class ParentScanSettings:
    where: WhereChoices
    alias: str
    timeout: int
    probes: int
    max_ttl: int
    force_explicit: bool
    ping_probes: int
    gateway_folder_path: str | None  # in combination with where == 'gateway_folder'


class ParentScanBackgroundJob(BackgroundJob):
    job_prefix = "parent_scan"

    @classmethod
    def gui_title(cls) -> str:
        return _("Parent scan")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def _back_url(self) -> str:
        return disk_or_search_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        ).url()

    def do_execute(
        self,
        settings: ParentScanSettings,
        tasks: Sequence[ParentScanTask],
        job_interface: BackgroundProcessInterface,
        *,
        pprint_value: bool,
        debug: bool,
    ) -> None:
        with job_interface.gui_context():
            self._initialize_statistics()
            self._logger.info("Parent scan started...")

            for task in tasks:
                self._process_task(task, settings, pprint_value=pprint_value, debug=debug)

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

    def _process_task(
        self, task: ParentScanTask, settings: ParentScanSettings, *, pprint_value: bool, debug: bool
    ) -> None:
        self._num_hosts_total += 1

        try:
            self._process_parent_scan_results(
                task,
                settings,
                self._execute_parent_scan(task, settings, debug=debug),
                pprint_value=pprint_value,
                debug=debug,
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

    def _execute_parent_scan(
        self, task: ParentScanTask, settings: ParentScanSettings, *, debug: bool
    ) -> Sequence[GatewayResult]:
        return scan_parents(
            automation_config=task.automation_config,
            host_name=task.host_name,
            timeout=settings.timeout,
            probes=settings.probes,
            max_ttl=settings.max_ttl,
            ping_probes=settings.ping_probes,
            debug=debug,
        ).results

    def _process_parent_scan_results(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        results: Sequence[GatewayResult],
        *,
        pprint_value: bool,
        debug: bool,
    ) -> None:
        for result in results:
            if result.state in ["direct", "root", "gateway"]:
                # The following code updates the host config. The progress from loading the Setup folder
                # until it has been saved needs to be locked.
                with store.lock_checkmk_configuration(configuration_lockfile):
                    self._configure_host_and_gateway(
                        task, settings, result.gateway, pprint_value=pprint_value, debug=debug
                    )
            else:
                self._logger.error(result.message)

            if result.gateway:
                self._num_gateways_found += 1

            if result.state in ["direct", "root"]:
                self._num_directly_reachable_hosts += 1

            self._num_unreachable_gateways += result.ping_fails

            if result.state == "notfound":
                self._num_no_gateway_found += 1

            if result.state in ["failed", "dnserror", "garbled"]:
                self._num_errors += 1

    def _configure_host_and_gateway(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        gateway: Gateway | None,
        *,
        pprint_value: bool,
        debug: bool,
    ) -> None:
        tree = folder_tree()
        tree.invalidate_caches()
        host_folder = tree.folder(task.host_folder_path)
        gateway_folder = (
            tree.folder(settings.gateway_folder_path) if settings.gateway_folder_path else None
        )

        parents = self._configure_gateway(
            task,
            settings,
            gateway,
            host_folder,
            gateway_folder,
            pprint_value=pprint_value,
            debug=debug,
        )

        if (host := host_folder.host(task.host_name)) is None:
            # This seems to never happen.
            # `host` being optional was revealed when `folder` was no longer `Any`.
            raise MKGeneralException("No host named '{task.host_name}'")

        if host.effective_attributes().get("parents") == parents:
            self._logger.info(
                "Parents unchanged at %s", (",".join(parents) if parents else _("none"))
            )
            return

        if (
            settings.force_explicit
            or host.folder().effective_attributes().get("parents") != parents
        ):
            host.update_attributes({"parents": parents}, pprint_value=pprint_value)
        elif "parents" in host.attributes:
            # Check which parents the host would have inherited
            host.clean_attributes(["parents"], pprint_value=pprint_value)

        if parents:
            self._logger.info("Set parents to %s", ",".join(parents))
        else:
            self._logger.info("Removed parents")

        self._num_new_parents_configured += 1

    def _configure_gateway(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        gateway: Gateway | None,
        host_folder: Folder,
        gateway_folder: Folder | None,
        *,
        pprint_value: bool,
        debug: bool,
    ) -> list[HostName]:
        """Ensure there is a gateway host in the Checkmk configuration (or raise an exception)

        If we have found a gateway, we need to know a matching host name from our configuration.
        If there is none, we can create one, if the users wants this. The automation for the parent
        scan already tries to find such a host within the site."""
        if not gateway:
            return []

        if gateway.existing_gw_host_name:
            return [gateway.existing_gw_host_name]  # Nothing needs to be created

        if settings.where == "nowhere":
            raise MKUserError(None, _("Need parent %s, but not allowed to create one") % gateway.ip)

        gw_folder = self._determine_gateway_folder(
            settings.where, host_folder, gateway_folder, pprint_value=pprint_value
        )
        gw_host_name = self._determine_gateway_host_name(task, gateway)
        gw_host_attributes = self._determine_gateway_attributes(task, settings, gateway, gw_folder)
        gw_folder.create_hosts(
            [(gw_host_name, gw_host_attributes, None)], pprint_value=pprint_value
        )
        bakery.try_bake_agents_for_hosts([gw_host_name], debug=debug)
        self._num_gateway_hosts_created += 1

        return [gw_host_name]

    def _determine_gateway_folder(
        self,
        where: str,
        host_folder: Folder,
        gateway_folder: Folder | None,
        *,
        pprint_value: bool,
    ) -> Folder:
        if where == "here":  # directly in current folder
            return disk_or_search_base_folder_from_request(
                request.var("folder"), request.get_ascii_input("host")
            )

        if where == "subfolder":
            current = disk_or_search_base_folder_from_request(
                request.var("folder"), request.get_ascii_input("host")
            )

            # Put new gateways in subfolder "Parents" of current
            # folder. Does this folder already exist?
            if current.has_subfolder("parents"):
                parents_folder = current.subfolder("parents")
                assert parents_folder is not None
                return parents_folder
            # Create new gateway folder
            return current.create_subfolder("parents", _("Parents"), {}, pprint_value=pprint_value)

        if where == "there":  # In same folder as host
            return host_folder

        if where == "gateway_folder":
            if gateway_folder is None:
                raise MKUserError(None, _("Expected specific gateway folder"))
            return gateway_folder

        raise NotImplementedError()

    def _determine_gateway_host_name(self, task: ParentScanTask, gateway: Gateway) -> HostName:
        if gateway.dns_name:
            return gateway.dns_name

        if task.site_id:
            return HostName("gw-{}-{}".format(task.site_id, gateway.ip.replace(".", "-")))

        return HostName("gw-%s" % (gateway.ip.replace(".", "-")))

    def _determine_gateway_attributes(
        self,
        task: ParentScanTask,
        settings: ParentScanSettings,
        gateway: Gateway,
        gw_folder: Folder,
    ) -> HostAttributes:
        new_host_attributes = HostAttributes(
            {
                "ipaddress": HostAddress(gateway.ip),
            }
        )

        if settings.alias:
            new_host_attributes["alias"] = settings.alias

        if gw_folder.site_id() != task.site_id:
            new_host_attributes["site"] = task.site_id

        return new_host_attributes


def start_parent_scan(
    hosts: Sequence[Host],
    job: ParentScanBackgroundJob,
    settings: ParentScanSettings,
    *,
    site_configs: Mapping[SiteId, SiteConfiguration],
    pprint_value: bool,
    debug: bool,
) -> Result[None, AlreadyRunningError | StartupError]:
    return job.start(
        JobTarget(
            callable=parent_scan_job_entry_point,
            args=ParentScanJobArgs(
                tasks=[
                    ParentScanTask(
                        site_id=host.site_id(),
                        automation_config=make_automation_config(site_configs[host.site_id()]),
                        host_folder_path=host.folder().path(),
                        host_name=host.name(),
                    )
                    for host in hosts
                ],
                settings=settings,
                pprint_value=pprint_value,
                debug=debug,
            ),
        ),
        InitialStatusArgs(
            title=_("Parent scan"),
            lock_wato=False,
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )


class ParentScanJobArgs(BaseModel, frozen=True):
    tasks: Sequence[ParentScanTask]
    settings: ParentScanSettings
    pprint_value: bool
    debug: bool


def parent_scan_job_entry_point(
    job_interface: BackgroundProcessInterface, args: ParentScanJobArgs
) -> None:
    ParentScanBackgroundJob().do_execute(
        args.settings, args.tasks, job_interface, pprint_value=args.pprint_value, debug=args.debug
    )
