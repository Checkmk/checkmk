#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from livestatus import SiteConfigurations, SiteId

from cmk.ccc import store

from cmk.utils.paths import var_dir
from cmk.utils.user import UserId

from cmk.gui.config import active_config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.message import Message, message_gui
from cmk.gui.site_config import get_site_config, is_wato_slave_site
from cmk.gui.sites import states
from cmk.gui.userdb import load_users
from cmk.gui.utils import gen_id
from cmk.gui.utils.roles import user_may
from cmk.gui.watolib.analyze_configuration import ACResultState, ACTestResult, perform_tests


@dataclass(frozen=True)
class _MarkerFileStore:
    folder: Path

    def marker_file(self, site_id: SiteId, site_version: str) -> Path:
        return self.folder / str(site_id) / site_version

    def save(
        self, site_id: SiteId, site_version: str, ac_test_results: Sequence[ACTestResult]
    ) -> None:
        marker_file = self.marker_file(site_id, site_version)
        store.makedirs(marker_file.parent)
        store.save_text_to_file(marker_file, json.dumps([repr(r) for r in ac_test_results]))

    def cleanup(self, site_id: SiteId) -> None:
        for filepath, _mtime in sorted(
            [
                (marker_file, marker_file.stat().st_mtime)
                for marker_file in list((self.folder / site_id).iterdir())
            ],
            key=lambda t: t[1],
            reverse=True,
        )[5:]:
            filepath.unlink(missing_ok=True)


def _filter_non_ok_ac_test_results(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
) -> Mapping[SiteId, Sequence[ACTestResult]]:
    return {
        s: not_ok_rs
        for s, rs in ac_test_results_by_site_id.items()
        if (not_ok_rs := [r for r in rs if r.state is not ACResultState.OK])
    }


def _filter_extension_managing_users(user_ids: Sequence[UserId]) -> Sequence[UserId]:
    return [u for u in user_ids if user_may(u, "wato.manage_mkps")]


def _format_ac_test_results(
    ac_test_results_by_site_id: Mapping[SiteId, Sequence[ACTestResult]],
) -> str:
    by_problem: dict[str, list[SiteId]] = {}
    for site_id, ac_test_results in ac_test_results_by_site_id.items():
        for ac_test_result in ac_test_results:
            by_problem.setdefault(ac_test_result.text, []).append(site_id)
    return "\n".join([f"{p}: {', '.join(sids)}" for p, sids in by_problem.items()])


def execute_deprecation_tests_and_notify_users() -> None:
    if is_wato_slave_site():
        return

    marker_file_store = _MarkerFileStore(Path(var_dir) / "deprecations")

    site_versions_by_site_id = {
        site_id: site_version
        for site_id, site_state in states().items()
        if (
            (site_version := site_state.get("program_version"))
            and not (marker_file_store.marker_file(site_id, site_version)).exists()
        )
    }

    if not (
        not_ok_ac_test_results := _filter_non_ok_ac_test_results(
            perform_tests(
                logger,
                active_config,
                request,
                SiteConfigurations(
                    {
                        site_id: get_site_config(active_config, site_id)
                        for site_id in site_versions_by_site_id
                    }
                ),
                categories=["deprecations"],
            )
        )
    ):
        return

    for site_id, ac_test_results in not_ok_ac_test_results.items():
        marker_file_store.save(site_id, site_versions_by_site_id[site_id], ac_test_results)
        marker_file_store.cleanup(site_id)

    # TODO at the moment we use the text attr for identifying a 'problem', eg.:
    # "Loading 'metrics/foo' failed: name 'perfometer_info' is not defined (!!)"
    ac_test_results_message = _format_ac_test_results(not_ok_ac_test_results)

    now = int(time.time())
    for user_id in _filter_extension_managing_users(list(load_users())):
        message_gui(
            user_id,
            Message(
                dest=("list", [user_id]),
                methods=["gui_hint"],
                text=ac_test_results_message,
                id=gen_id(),
                time=now,
                security=False,
                acknowledged=False,
            ),
        )


def register(cron_job_registry: CronJobRegistry) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_deprecation_tests_and_notify_users",
            callable=execute_deprecation_tests_and_notify_users,
            interval=datetime.timedelta(days=1),
        )
    )
