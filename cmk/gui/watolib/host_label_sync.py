#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Synchronize discovered host labels from remote site to central site"""

from __future__ import annotations

import ast
import os
import time
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import timedelta
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any

from livestatus import SiteConfiguration

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

import cmk.utils.paths
from cmk.utils.labels import DiscoveredHostLabelsStore

from cmk.gui.config import Config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import has_wato_slave_sites, wato_slave_sites
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    MKAutomationException,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host
from cmk.gui.watolib.paths import wato_var_dir

UpdatedHostLabelsEntry = tuple[str, float, str]

_PATH_LAST_CLEANUP_TIMESTAMP = wato_var_dir() / "last_discovered_host_labels_cleanup.mk"
_MINIMUM_CLEANUP_INTERVAL = 60 * 60


@dataclass
class SiteResult:
    site_id: SiteId
    success: bool
    error: str
    updated_host_labels: list[UpdatedHostLabelsEntry]


@dataclass
class EnforcedHostRequest:
    site_id: SiteId
    host_name: HostName


@dataclass
class SiteRequest:
    newest_host_labels: float
    enforce_host: EnforcedHostRequest | None
    debug: bool

    @classmethod
    def deserialize(cls, serialized: dict[str, Any]) -> SiteRequest:
        enforce_host = (
            EnforcedHostRequest(**serialized["enforce_host"])
            if serialized["enforce_host"]
            else None
        )

        if enforce_host:
            host = Host.host(enforce_host.host_name)
            if host is None:
                raise MKGeneralException(
                    _(
                        "Host %s does not exist on remote site %s. This "
                        "may be caused by a failed configuration synchronization. Have a look at "
                        'the <a href="wato.py?folder=&mode=changelog">activate changes page</a> '
                        "for further information."
                    )
                    % (enforce_host.host_name, enforce_host.site_id)
                )
            host.permissions.need_permission("read")

        newest_host_labels = serialized["newest_host_labels"]
        assert isinstance(newest_host_labels, float)

        # .get() can be replaced by [] with 2.6
        debug = serialized.get("debug", False)
        assert isinstance(debug, bool)

        return cls(newest_host_labels, enforce_host, debug)

    def serialize(self) -> dict[str, Any]:
        return {
            "newest_host_labels": self.newest_host_labels,
            "enforce_host": asdict(self.enforce_host) if self.enforce_host else None,
            "debug": self.debug,
        }


@dataclass
class DiscoveredHostLabelSyncResponse:
    updated_host_labels: list[UpdatedHostLabelsEntry]


def register(cron_job_registry: CronJobRegistry) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_host_label_sync_job",
            callable=execute_host_label_sync_job,
            interval=timedelta(minutes=1),
            run_in_thread=True,
        )
    )


def execute_host_label_sync(
    host_name: HostName, automation_config: RemoteAutomationConfig, *, debug: bool
) -> None:
    """Contacts the given remote site to synchronize the labels of the given host"""
    result = _execute_site_sync(
        automation_config,
        SiteRequest(
            newest_host_labels=0.0,
            enforce_host=EnforcedHostRequest(automation_config.site_id, host_name),
            debug=debug,
        ),
    )
    save_updated_host_label_files(result.updated_host_labels)


def execute_host_label_sync_job(config: Config) -> None:
    """This function is called by the GUI cron job once a minute.
    Errors are logged to var/log/web.log."""
    if not has_wato_slave_sites():
        return

    DiscoveredHostLabelSyncJob().do_sync(remote_sites=wato_slave_sites(), debug=config.debug)

    now = time.time()
    if (
        now - _load_and_parse_timestamp_last_cleanup_defensive(_PATH_LAST_CLEANUP_TIMESTAMP)
        < _MINIMUM_CLEANUP_INTERVAL
    ):
        return

    _cleanup_discovered_host_labels(
        cmk.utils.paths.discovered_host_labels_dir,
        folder_tree().root_folder().all_hosts_recursively(),
    )
    store.save_text_to_file(_PATH_LAST_CLEANUP_TIMESTAMP, str(now))


class DiscoveredHostLabelSyncJob:
    """This job synchronizes the discovered host labels from remote sites to the central site

    Currently they are only needed for the Agent Bakery, but may be used in other places in the
    future.
    """

    def do_sync(self, *, remote_sites: Mapping[SiteId, SiteConfiguration], debug: bool) -> None:
        logger.info("Synchronization started...")
        self._execute_sync(remote_sites, debug=debug)
        logger.info("The synchronization finished.")

    def _execute_sync(
        self, remote_sites: Mapping[SiteId, SiteConfiguration], *, debug: bool
    ) -> None:
        newest_host_labels = self._load_newest_host_labels_per_site()

        with ThreadPool(20) as pool:
            results = pool.map(
                copy_request_context(self._execute_site_sync_bg),
                [
                    (
                        RemoteAutomationConfig.from_site_config(site_spec),
                        SiteRequest(newest_host_labels.get(site_id, 0.0), None, debug=debug),
                    )
                    for site_id, site_spec in remote_sites.items()
                ],
            )

        self._process_site_sync_results(newest_host_labels, results)

    def _execute_site_sync_bg(
        self,
        args: tuple[
            RemoteAutomationConfig,
            SiteRequest,
        ],
    ) -> SiteResult:
        return _execute_site_sync(*args)

    def _process_site_sync_results(
        self, newest_host_labels: dict[SiteId, float], results: list[SiteResult]
    ) -> None:
        """Persist the sync results received from the remote site on the central site"""
        for site_result in results:
            if not site_result.updated_host_labels:
                continue

            newest_host_labels[site_result.site_id] = max(
                [newest_host_labels.get(site_result.site_id, 0.0)]
                + [e[1] for e in site_result.updated_host_labels]
            )
            save_updated_host_label_files(site_result.updated_host_labels)

        self._save_newest_host_labels_per_site(newest_host_labels)

    @staticmethod
    def newest_host_labels_per_site_path() -> Path:
        return wato_var_dir() / "newest_host_labels_per_site.mk"

    def _load_newest_host_labels_per_site(self) -> dict[SiteId, float]:
        return store.load_object_from_file(
            DiscoveredHostLabelSyncJob.newest_host_labels_per_site_path(), default={}
        )

    def _save_newest_host_labels_per_site(self, newest_host_labels: dict[SiteId, float]) -> None:
        store.save_object_to_file(
            DiscoveredHostLabelSyncJob.newest_host_labels_per_site_path(), newest_host_labels
        )


def _execute_site_sync(
    automation_config: RemoteAutomationConfig, site_request: SiteRequest
) -> SiteResult:
    """Executes the sync with a site. Is executed in a dedicated subprocess (One per site)"""
    try:
        logger.debug(_("[%s] Starting sync for site"), automation_config.site_id)

        # timeout=100: Use a value smaller than the default apache request timeout
        raw_result = do_remote_automation(
            automation_config,
            "discovered-host-label-sync",
            [
                ("request", repr(site_request.serialize())),
            ],
            timeout=100,
            debug=site_request.debug,
        )
        assert isinstance(raw_result, dict)
        result = DiscoveredHostLabelSyncResponse(**raw_result)

        logger.debug(_("[%s] Finished sync for site"), automation_config.site_id)
        return SiteResult(
            site_id=automation_config.site_id,
            success=True,
            error="",
            updated_host_labels=result.updated_host_labels,
        )

    except MKAutomationException as e:
        return SiteResult(
            site_id=automation_config.site_id,
            success=False,
            error=str(e),
            updated_host_labels=[],
        )

    except Exception as e:
        logger.error(
            "Failed to get discovered host labels from site %s: %s", automation_config.site_id, e
        )
        return SiteResult(
            site_id=automation_config.site_id,
            success=False,
            error=str(e),
            updated_host_labels=[],
        )


def get_host_labels_entry_of_host(host_name: HostName) -> UpdatedHostLabelsEntry:
    """Returns the host labels entry of the given host"""
    path = DiscoveredHostLabelsStore(host_name).file_path
    with path.open() as f:
        return (path.name, path.stat().st_mtime, f.read())


def save_updated_host_label_files(updated_host_labels: list[UpdatedHostLabelsEntry]) -> None:
    """Persists the data previously read by get_updated_host_label_files()"""
    for file_name, mtime, content in updated_host_labels:
        file_path = cmk.utils.paths.discovered_host_labels_dir / file_name
        store.save_text_to_file(file_path, content)
        os.utime(file_path, (mtime, mtime))


def get_updated_host_label_files(newer_than: float) -> list[UpdatedHostLabelsEntry]:
    """Returns the host label file content + meta data which are newer than the given timestamp"""
    updated_host_labels = []
    for path in sorted(cmk.utils.paths.discovered_host_labels_dir.glob("*.mk")):
        mtime = path.stat().st_mtime
        if path.stat().st_mtime <= newer_than:
            continue  # Already known to central site

        with path.open() as f:
            updated_host_labels.append((path.name, mtime, f.read()))
    return updated_host_labels


class AutomationDiscoveredHostLabelSync(AutomationCommand[SiteRequest]):
    """Called by execute_site_sync to perform the sync with a remote site"""

    def command_name(self) -> str:
        return "discovered-host-label-sync"

    def get_request(self) -> SiteRequest:
        ascii_input = request.get_ascii_input("request")
        if ascii_input is None:
            raise MKUserError("request", _('The parameter "%s" is missing.') % "request")
        return SiteRequest.deserialize(ast.literal_eval(ascii_input))

    def execute(self, api_request: SiteRequest) -> dict[str, Any]:
        if api_request.enforce_host:
            try:
                response = DiscoveredHostLabelSyncResponse(
                    [get_host_labels_entry_of_host(api_request.enforce_host.host_name)]
                )
            except FileNotFoundError:
                response = DiscoveredHostLabelSyncResponse([])
        else:
            response = DiscoveredHostLabelSyncResponse(
                get_updated_host_label_files(newer_than=api_request.newest_host_labels)
            )

        return asdict(response)


def _load_and_parse_timestamp_last_cleanup_defensive(path: Path) -> float:
    try:
        raw_timestamp_last_cleanup = path.read_text()
    except FileNotFoundError:
        raw_timestamp_last_cleanup = str(0.0)
    try:
        return float(raw_timestamp_last_cleanup)
    except ValueError:
        return 0.0


def _cleanup_discovered_host_labels(
    discovered_host_labels_dir: Path,
    all_known_hosts: Iterable[str],
) -> None:
    hosts_with_stored_discovered_host_labels = {
        p.stem for p in discovered_host_labels_dir.iterdir()
    }
    for removed_host_with_still_stored_discovered_host_labels in (
        hosts_with_stored_discovered_host_labels - set(all_known_hosts)
    ):
        (
            discovered_host_labels_dir
            / f"{removed_host_with_still_stored_discovered_host_labels}.mk"
        ).unlink(missing_ok=True)
