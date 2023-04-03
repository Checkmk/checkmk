#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import json
import time
from collections.abc import Iterable, Iterator, Sequence
from typing import Literal, TypedDict

from livestatus import LocalConnection, SiteId

from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject, RuleSpec
from cmk.utils.type_defs import HostName

from cmk.base.export import get_ruleset_matcher  # pylint: disable=cmk-module-layer-violation

from cmk.gui.background_job import BackgroundJob, BackgroundProcessInterface, InitialStatusArgs
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.session import SuperUserContext
from cmk.gui.site_config import get_site_config, is_wato_slave_site, site_is_local, wato_site_ids
from cmk.gui.valuespec import Seconds
from cmk.gui.watolib.activate_changes import ActivateChangesManager
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.hosts_and_folders import CREHost, Host
from cmk.gui.watolib.rulesets import SingleRulesetRecursively, UseHostFolder


def execute_host_removal_background_job() -> None:
    if is_wato_slave_site():
        return

    job = HostRemovalBackgroundJob()
    if job.is_active():
        logger.debug("Another host removal job is already running, skipping this time.")
        return

    job.start(_remove_hosts)


class HostRemovalBackgroundJob(BackgroundJob):
    job_prefix = "host_removal"

    @classmethod
    def gui_title(cls) -> str:
        return _("Host removal")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                lock_wato=False,
                stoppable=False,
            ),
        )


def _remove_hosts(job_interface: BackgroundProcessInterface) -> None:
    job_interface.send_progress_update("Starting host removal background job")

    if not (
        hosts_to_be_removed := {
            site_id: hosts
            for site_id, hosts_iter in _hosts_to_be_removed(job_interface)
            if (hosts := list(hosts_iter))
        }
    ):
        job_interface.send_progress_update("Found no hosts to be removed, exiting")
        return

    for folder, hosts_in_folder in itertools.groupby(
        itertools.chain.from_iterable(hosts_to_be_removed.values()),
        lambda h: h.folder(),
    ):
        hostnames = list(host.name() for host in hosts_in_folder)
        job_interface.send_progress_update(
            f"Removing {len(hostnames)} hosts from folder {folder.title()}"
        )
        with SuperUserContext():
            folder.delete_hosts(hostnames, automation=delete_hosts)

    job_interface.send_progress_update("Hosts removed, starting activation of changes")
    _activate_changes(hosts_to_be_removed)

    job_interface.send_progress_update("Host removal background job finished")


def _hosts_to_be_removed(
    job_interface: BackgroundProcessInterface,
) -> Iterator[tuple[SiteId, Iterator[CREHost]]]:
    yield from (
        (site_id, _hosts_to_be_removed_for_site(job_interface, site_id))
        for site_id in wato_site_ids()
    )


def _hosts_to_be_removed_for_site(
    job_interface: BackgroundProcessInterface,
    site_id: SiteId,
) -> Iterator[CREHost]:
    if site_is_local(site_id):
        hostnames = _hosts_to_be_removed_local()
    else:
        try:
            hostnames_serialized = str(
                do_remote_automation(
                    get_site_config(site_id),
                    "hosts-for-auto-removal",
                    [],
                )
            )
        except MKUserError:  # Site may be down
            job_interface.send_progress_update(f"Skipping remote site {site_id}, might be down")
            return
        hostnames = json.loads(hostnames_serialized)

    yield from (Host.load_host(hostname) for hostname in hostnames)


def _hosts_to_be_removed_local() -> Iterator[HostName]:
    if not (automatic_host_removal_ruleset := _load_automatic_host_removal_ruleset()):
        return  # small 'optimization'
    ruleset_matcher = get_ruleset_matcher()
    now = time.time()

    for hostname, check_mk_service_crit_since in _livestatus_query_local_candidates():
        try:
            rule_value = next(
                ruleset_matcher.get_host_ruleset_values(
                    match_object=RulesetMatchObject(hostname),
                    ruleset=automatic_host_removal_ruleset,
                    is_binary=False,
                )
            )
        except StopIteration:
            continue
        if _should_delete_host(
            rule_value=rule_value,
            check_mk_service_crit_for=now - check_mk_service_crit_since,
        ):
            yield hostname


def _load_automatic_host_removal_ruleset() -> Sequence[RuleSpec]:
    return [
        rule.to_config(use_host_folder=UseHostFolder.HOST_FOLDER_FOR_BASE)
        for _folder, _idx, rule in SingleRulesetRecursively.load_single_ruleset_recursively(
            "automatic_host_removal"
        )
        .get("automatic_host_removal")
        .get_rules()
    ]


def _livestatus_query_local_candidates() -> Iterator[tuple[HostName, int]]:
    yield from (
        (HostName(hostname), int(crit_since))
        for hostname, crit_since in LocalConnection().query_table(
            """GET services
Columns: host_name last_state_change
Filter: description = Check_MK
Filter: state = 2"""
        )
    )


class _RemovalConditions(TypedDict):
    checkmk_service_crit: Seconds


def _should_delete_host(
    *,
    rule_value: tuple[Literal["enabled"], _RemovalConditions] | tuple[Literal["disabled"], None],
    check_mk_service_crit_for: float,
) -> bool:
    # TODO: use a match statement once mypy can handle this
    if rule_value[0] == "enabled":
        return check_mk_service_crit_for >= rule_value[1]["checkmk_service_crit"]
    return False


def _activate_changes(sites: Iterable[SiteId]) -> None:
    manager = ActivateChangesManager()
    manager.load()
    with SuperUserContext():
        manager.start(list(sites), activate_foreign=True)


class AutomationHostsForAutoRemoval(AutomationCommand):
    def command_name(self) -> str:
        return "hosts-for-auto-removal"

    def execute(self, api_request: object = None) -> str:
        return json.dumps(list(_hosts_to_be_removed_local()))

    def get_request(self) -> None:
        pass
