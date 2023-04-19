#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from livestatus import SiteId

import cmk.utils.store as store

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    job_registry,
)
from cmk.gui.cron import register_job
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import get_site_config, is_wato_slave_site, wato_slave_sites
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.paths import wato_var_dir


@automation_command_registry.register
class AutomationGetAuditLogs(AutomationCommand):
    def command_name(self) -> str:
        return "get-audit-logs"

    def execute(self, api_request: int) -> str:
        audit_log_store = AuditLogStore(AuditLogStore.make_path())
        return audit_log_store.to_json(audit_log_store.get_entries_since(timestamp=api_request))

    def get_request(self) -> int:
        return int(request.get_str_input_mandatory("last_audit_log_timestamp"))


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


@job_registry.register
class GetRemoteAuditLogsBackgroundJob(BackgroundJob):
    job_prefix = "get_remote_audit_logs"

    @classmethod
    def gui_title(cls):
        return _("Get remote audit logs")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                lock_wato=False,
                stoppable=False,
            ),
        )
        self._last_audit_log_timestamps_path = _get_last_audit_log_timestamps_path()
        self._last_audit_log_timestamps_store = LastAuditLogTimestampsStore(
            self._last_audit_log_timestamps_path
        )
        self._audit_log_store_path = AuditLogStore.make_path()
        self._audit_log_store = AuditLogStore(self._audit_log_store_path)

    def do_execute(self, job_interface: BackgroundProcessInterface) -> None:
        with store.locked(self._last_audit_log_timestamps_path):
            prev_last_timestamps = self._last_audit_log_timestamps_store.load()

        (
            failed_sites,
            last_audit_logs,
            last_timestamps,
        ) = self._get_last_audit_logs(prev_last_timestamps)

        if failed_sites:
            job_interface.send_progress_update(
                _("Failed to get audit logs from sites: %s.") % ", ".join(sorted(failed_sites))
            )

        if last_audit_logs:
            with store.locked(self._audit_log_store_path):
                audit_logs_from_remote_sites = self._store_audit_logs(last_audit_logs)

        with store.locked(self._last_audit_log_timestamps_path):
            self._last_audit_log_timestamps_store.write(last_timestamps)

        if not last_audit_logs:
            job_interface.send_result_message(_("No remote audit logs processed."))
            return

        job_interface.send_result_message(
            _("Successfully got audit logs from sites: %s<br>%s")
            % (
                ", ".join(sorted(audit_logs_from_remote_sites)),
                "<br>".join(
                    [
                        f"{site_id}: {len(audit_logs)}"
                        for site_id, audit_logs in sorted(
                            last_audit_logs.items(),
                            key=lambda t: (t[0], t[1]),
                        )
                    ],
                ),
            )
        )

    def _get_last_audit_logs(
        self,
        prev_last_timestamps: dict[SiteId, int],
    ) -> tuple[set[SiteId], Mapping[SiteId, Sequence[AuditLogStore.Entry]], Mapping[SiteId, int]]:
        now = int(time.time())
        wato_slave_site_ids = set(wato_slave_sites())

        failed_sites: set[SiteId] = set()
        last_audit_logs: dict[SiteId, Sequence[AuditLogStore.Entry]] = {}

        for site_id in wato_slave_site_ids:
            since = prev_last_timestamps.get(site_id, now)
            logger.debug("Getting audit logs from site %s since %s", site_id, since)

            try:
                last_audit_logs_of_site = self._get_last_audit_logs_of_site(site_id, since)
            except Exception as e:
                failed_sites.add(site_id)
                logger.error("Failed to get audit logs from site %s: %s", site_id, e)
                continue

            if last_audit_logs_of_site:
                last_audit_logs[site_id] = last_audit_logs_of_site
                # Audit logs are already sorted.
                timestamp = last_audit_logs_of_site[-1].time
            else:
                timestamp = since

            prev_last_timestamps[site_id] = timestamp

        # Housekeeping:
        # Remove entries for which the timestamp is older than a 30 days if and only if the site
        # is not active, ie. not in 'wato_slave_site_ids'.
        last_timestamps = {
            site_id: timestamp
            for site_id, timestamp in prev_last_timestamps.items()
            if site_id in wato_slave_site_ids or (now - timestamp) < (30 * 7 * 24 * 3600)
        }

        return failed_sites, last_audit_logs, last_timestamps

    def _get_last_audit_logs_of_site(
        self, site_id: SiteId, last_audit_log_timestamp: int
    ) -> Sequence[AuditLogStore.Entry]:
        return self._audit_log_store.from_json(
            str(
                do_remote_automation(
                    get_site_config(site_id),
                    "get-audit-logs",
                    [("last_audit_log_timestamp", str(last_audit_log_timestamp))],
                )
            )
        )

    def _store_audit_logs(
        self, last_audit_logs: Mapping[SiteId, Sequence[AuditLogStore.Entry]]
    ) -> set[SiteId]:
        audit_logs_counter: Counter = Counter()
        central_site_entries = self._audit_log_store.read()
        audit_logs_from_remote_sites: set[SiteId] = set()

        for site_id, entries in last_audit_logs.items():
            for entry in entries:
                if entry not in central_site_entries:
                    audit_logs_counter.update({site_id: 1})
                    central_site_entries.append(entry)
                    audit_logs_from_remote_sites.add(site_id)

        self._audit_log_store.write(central_site_entries)

        for site_id, num_entries in audit_logs_counter.items():
            logger.debug("Wrote %s audit log entries from site %s", num_entries, site_id)

        return audit_logs_from_remote_sites


def execute_get_remote_audit_logs() -> None:
    if is_wato_slave_site():
        return

    job = GetRemoteAuditLogsBackgroundJob()
    if job.is_active():
        logger.debug("Another 'get remote audit logs' job is already running: Skipping this time.")
        return

    job.start(job.do_execute)


register_job(execute_get_remote_audit_logs)
