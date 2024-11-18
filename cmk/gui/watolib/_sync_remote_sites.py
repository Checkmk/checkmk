#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from livestatus import SiteId

from cmk.ccc import store
from cmk.ccc.site import omd_site

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.config import active_config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.site_config import get_site_config, is_wato_slave_site, wato_slave_sites
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.automation_commands import AutomationCommand, AutomationCommandRegistry
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.paths import wato_var_dir
from cmk.gui.watolib.site_changes import ChangeSpec, SiteChanges

AuditLogs = Sequence[AuditLogStore.Entry]
SiteChangeSequence = Sequence[ChangeSpec]
LastAuditLogs = Mapping[SiteId, AuditLogs]
LastSiteChanges = Mapping[SiteId, SiteChangeSequence]


def register(
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_sync_remote_sites",
            callable=execute_sync_remote_sites,
            interval=timedelta(minutes=1),
        )
    )
    job_registry.register(SyncRemoteSitesBackgroundJob)

    automation_command_registry.register(AutomationSyncRemoteSites)
    automation_command_registry.register(AutomationClearSiteChanges)


@dataclass
class SyncRemoteSitesResult:
    audit_logs: Sequence[AuditLogStore.Entry]
    site_changes: Sequence[ChangeSpec]

    def to_json(self) -> str:
        audit_logs = AuditLogStore.to_json(self.audit_logs)
        site_changes = SiteChanges.to_json(self.site_changes)

        return json.dumps((audit_logs, site_changes))

    @classmethod
    def from_json(cls, serialized_result: str) -> "SyncRemoteSitesResult":
        audit_logs_raw, site_changes_raw = json.loads(serialized_result)

        audit_logs = AuditLogStore.from_json(audit_logs_raw)
        site_changes = SiteChanges.from_json(site_changes_raw)

        return cls(audit_logs, site_changes)


class AutomationSyncRemoteSites(AutomationCommand[int]):
    def command_name(self) -> str:
        return "sync-remote-site"

    def execute(self, api_request: int) -> str:
        site_id = omd_site()

        audit_logs = AuditLogStore().get_entries_since(timestamp=api_request)
        site_changes = SiteChanges(site_id).read()

        return SyncRemoteSitesResult(audit_logs, site_changes).to_json()

    def get_request(self) -> int:
        return int(request.get_str_input_mandatory("last_audit_log_timestamp"))


class AutomationClearSiteChanges(AutomationCommand[None]):
    def command_name(self) -> str:
        return "clear-site-changes"

    def execute(self, api_request: None) -> None:
        site_id = omd_site()
        SiteChanges(site_id).clear()

    def get_request(self) -> None:
        pass


class LastAuditLogTimestampsStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[SiteId, int]:
        raw_timestamps = store.load_text_from_file(
            self._path,
            default="{}",
        )

        try:
            return json.loads(raw_timestamps)
        except json.decoder.JSONDecodeError:
            return {}

    def write(self, timestamps: Mapping[SiteId, int]) -> None:
        store.save_text_to_file(self._path, json.dumps(timestamps))


def _get_last_audit_log_timestamps_path() -> Path:
    return wato_var_dir() / "log" / "last_audit_log_timestamps"


class SyncRemoteSitesBackgroundJob(BackgroundJob):
    job_prefix = "sync_remote_sites"

    @classmethod
    def gui_title(cls) -> str:
        return _("Sync remote site changes and audit log")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)
        self._last_audit_log_timestamps_path = _get_last_audit_log_timestamps_path()
        self._last_audit_log_timestamps_store = LastAuditLogTimestampsStore(
            self._last_audit_log_timestamps_path
        )
        self._audit_log_store = AuditLogStore()

    def shall_start(self) -> bool:
        """Some basic preliminary check to decide quickly whether to start the job"""
        return bool(wato_slave_sites())

    def do_execute(self, job_interface: BackgroundProcessInterface) -> None:
        with job_interface.gui_context():
            self._execute(job_interface)

    def _execute(self, job_interface: BackgroundProcessInterface) -> None:
        with store.locked(self._last_audit_log_timestamps_path):
            prev_last_timestamps = self._last_audit_log_timestamps_store.load()

        (
            failed_sites,
            last_audit_logs,
            last_site_changes,
            last_timestamps,
        ) = self._get_remote_changes(prev_last_timestamps)

        if failed_sites:
            job_interface.send_progress_update(
                _("Failed to get changes from sites: %s.") % ", ".join(sorted(failed_sites))
            )

        audit_logs_synced_sites = (
            self._store_audit_logs(last_audit_logs) if last_audit_logs else None
        )
        site_changes_synced_sites = (
            self._store_site_changes(last_site_changes) if last_site_changes else None
        )

        if site_changes_synced_sites:
            logger.debug(
                "Removing site changes from sites: %s.", ", ".join(site_changes_synced_sites)
            )
            self._clear_site_changes_from_remote_sites(site_changes_synced_sites)

        with store.locked(self._last_audit_log_timestamps_path):
            self._last_audit_log_timestamps_store.write(last_timestamps)

        job_interface.send_result_message(
            self._get_result_message(last_audit_logs, audit_logs_synced_sites, "audit logs")
        )

        job_interface.send_result_message(
            self._get_result_message(last_site_changes, site_changes_synced_sites, "site changes")
        )

    def _get_remote_changes(
        self,
        prev_last_timestamps: dict[SiteId, int],
    ) -> tuple[
        set[SiteId],
        Mapping[SiteId, AuditLogs],
        Mapping[SiteId, SiteChangeSequence],
        Mapping[SiteId, int],
    ]:
        now = int(time.time())
        wato_slave_site_ids = set(wato_slave_sites())

        failed_sites: set[SiteId] = set()
        last_audit_logs: dict[SiteId, AuditLogs] = {}
        last_site_changes: dict[SiteId, SiteChangeSequence] = {}

        for site_id in wato_slave_site_ids:
            since = prev_last_timestamps.get(site_id, now)
            logger.debug("Getting audit logs from site %s since %s", site_id, since)
            logger.debug("Getting site changes from site %s", site_id)

            try:
                sync_result = self._sync_remote_site(site_id, since)
            except Exception as e:
                failed_sites.add(site_id)
                logger.error(
                    "Failed to get audit logs and site changes from site %s: %s", site_id, e
                )
                continue

            if sync_result.audit_logs:
                last_audit_logs[site_id] = sync_result.audit_logs
                # Audit logs are already sorted.
                timestamp = sync_result.audit_logs[-1].time
            else:
                timestamp = since

            if sync_result.site_changes:
                last_site_changes[site_id] = sync_result.site_changes

            prev_last_timestamps[site_id] = timestamp

        # Housekeeping:
        # Remove entries for which the timestamp is older than a 30 days if and only if the site
        # is not active, ie. not in 'wato_slave_site_ids'.
        last_timestamps = {
            site_id: timestamp
            for site_id, timestamp in prev_last_timestamps.items()
            if site_id in wato_slave_site_ids or (now - timestamp) < (30 * 7 * 24 * 3600)
        }

        return failed_sites, last_audit_logs, last_site_changes, last_timestamps

    def _sync_remote_site(
        self, site_id: SiteId, last_audit_log_timestamp: int
    ) -> SyncRemoteSitesResult:
        return SyncRemoteSitesResult.from_json(
            str(
                do_remote_automation(
                    get_site_config(active_config, site_id),
                    "sync-remote-site",
                    [("last_audit_log_timestamp", str(last_audit_log_timestamp))],
                )
            )
        )

    def _store_audit_logs(self, last_audit_logs: LastAuditLogs) -> set[SiteId]:
        counter: Counter = Counter()
        for site_id, entries in last_audit_logs.items():
            for entry in entries:
                counter.update({site_id: 1})
                self._audit_log_store.append(entry)

        return set(counter.keys())

    def _store_site_changes(self, last_site_changes: LastSiteChanges) -> set[SiteId]:
        counter: Counter = Counter()
        for site_id, entries in last_site_changes.items():
            with SiteChanges(site_id).mutable_view() as site_entries:
                for entry in entries:
                    if entry not in site_entries:
                        site_entries.append(entry)
                        counter.update({site_id: 1})

        self._write_log(counter, "site change")
        return set(counter.keys())

    def _write_log(self, counter: Counter, change_name: str) -> None:
        for site_id, num_entries in counter.items():
            logger.debug("Wrote %s %s entries from site %s", num_entries, change_name, site_id)

    def _clear_site_changes_from_remote_sites(self, site_changes_synced_sites: set[SiteId]) -> None:
        for site_id in site_changes_synced_sites:
            do_remote_automation(get_site_config(active_config, site_id), "clear-site-changes", [])

    def _get_result_message(
        self,
        last_changes: LastAuditLogs | LastSiteChanges,
        synced_remote_sites: set[SiteId] | None,
        change_name: str,
    ) -> str:
        if not last_changes or not synced_remote_sites:
            return _("No remote %s processed.") % change_name

        return _("Successfully got %s from sites: %s<br>%s") % (
            change_name,
            ", ".join(sorted(synced_remote_sites)),
            "<br>".join(
                [
                    f"{site_id}: {len(changes)}"
                    for site_id, changes in sorted(
                        last_changes.items(),
                        key=lambda t: (t[0], t[1]),
                    )
                ],
            ),
        )


def execute_sync_remote_sites() -> None:
    if is_wato_slave_site():
        return

    job = SyncRemoteSitesBackgroundJob()
    if job.is_active():
        logger.debug("Another 'sync remote sites' job is already running: Skipping this time.")
        return

    if not job.shall_start():
        logger.debug("Job shall not start")
        return

    job.start(
        job.do_execute,
        InitialStatusArgs(
            title=SyncRemoteSitesBackgroundJob.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )
