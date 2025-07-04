#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import json
import time
from collections.abc import Collection, Iterator, Mapping, Sequence
from logging import FileHandler, Formatter
from typing import Literal, TypedDict

from redis import ConnectionError as RedisConnectionError

from livestatus import LocalConnection, MKLivestatusSocketError

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils.paths import log_dir
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

import cmk.gui.log
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.session import SuperUserContext
from cmk.gui.site_config import is_wato_slave_site, wato_site_ids
from cmk.gui.watolib.activate_changes import ActivateChangesManager
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    LocalAutomationConfig,
    make_automation_config,
    MKAutomationException,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.check_mk_automations import analyze_host_rule_matches, delete_hosts
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.rulesets import SingleRulesetRecursively, UseHostFolder

_LOGGER = cmk.gui.log.logger.getChild("automatic_host_removal")
_LOGGER_BACKGROUND_JOB = _LOGGER.getChild("background_job")


def execute_host_removal_job(config: Config) -> None:
    if is_wato_slave_site():
        return

    if not _load_automatic_host_removal_ruleset():
        _LOGGER.debug("Automatic host removal not configured")
        return

    _init_logging()

    _LOGGER_BACKGROUND_JOB.debug("Starting host removal background job")

    def _folder_of_host(h: Host) -> Folder:
        return h.folder()

    try:
        _LOGGER.info("Starting host removal background job")

        if not (
            hosts_to_be_removed := {
                site_id: hosts
                for site_id, hosts in _hosts_to_be_removed(
                    automation_configs={
                        site_id: make_automation_config(
                            config.sites[site_id],
                        )
                        for site_id in wato_site_ids()
                    },
                    debug=config.debug,
                )
                if hosts
            }
        ):
            _LOGGER_BACKGROUND_JOB.debug("Found no hosts to be removed, exiting")
            _LOGGER.info("Found no hosts to be removed, exiting")
            return
        for folder, hosts_in_folder in itertools.groupby(
            itertools.chain.from_iterable(hosts_to_be_removed.values()), _folder_of_host
        ):
            hostnames = list(host.name() for host in hosts_in_folder)
            _LOGGER_BACKGROUND_JOB.debug(
                "Removing %d host(s) from folder %s",
                len(hostnames),
                folder.title(),
            )
            _LOGGER.info(f"Removing {len(hostnames)} hosts from folder {folder.title()}")
            with SuperUserContext():
                folder.delete_hosts(
                    hostnames,
                    automation=delete_hosts,
                    pprint_value=config.wato_pprint_config,
                    debug=config.debug,
                )

        _LOGGER.info("Hosts removed, starting activation of changes")
        _activate_changes(hosts_to_be_removed, debug=config.debug)

        _LOGGER.info("Host removal background job finished")
    except RedisConnectionError as e:
        # This can happen when Redis or the whole site is stopped while the background job is
        # running. Report an error in the background job result but don't create a crash report.
        _LOGGER.warning(_("An connection error occurred: %s") % e)


def _init_logging() -> None:
    handler = FileHandler(log_file := log_dir / "automatic-host-removal.log", encoding="utf-8")
    _LOGGER.info("Logging host removal to %s", log_file)
    handler.setFormatter(Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s"))
    del _LOGGER.handlers[:]  # Remove all previously existing handlers
    _LOGGER.addHandler(handler)
    _LOGGER.propagate = False


def _hosts_to_be_removed(
    *,
    automation_configs: Mapping[SiteId, LocalAutomationConfig | RemoteAutomationConfig],
    debug: bool,
) -> list[tuple[SiteId, list[Host]]]:
    _LOGGER_BACKGROUND_JOB.info("Gathering hosts to be removed")
    return [
        (site_id, _hosts_to_be_removed_for_site(site_id, automation_configs[site_id], debug=debug))
        for site_id in wato_site_ids()
    ]


def _hosts_to_be_removed_for_site(
    site_id: SiteId,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    *,
    debug: bool,
) -> list[Host]:
    if isinstance(automation_config, LocalAutomationConfig):
        try:
            # evaluate the generator here to potentially catch the exception below
            hostnames = list(_hosts_to_be_removed_local(debug=debug))
        # can happen if the Nagios core is currently restarting during the activation of changes
        except MKLivestatusSocketError:
            _LOGGER.info(
                f"Skipping local site {site_id}, since livestatus is not available",
                exc_info=True,
            )
            return []
    else:
        try:
            hostnames_serialized = str(
                do_remote_automation(
                    automation_config,
                    "hosts-for-auto-removal",
                    [],
                    debug=debug,
                )
            )
        except (MKUserError, MKAutomationException) as e:
            _LOGGER.info(f"Skipping remote site {site_id}, might be down or not logged in ({e})")
            return []
        hostnames = json.loads(hostnames_serialized)

    return [Host.load_host(hostname) for hostname in hostnames]


def _hosts_to_be_removed_local(*, debug: bool) -> Iterator[HostName]:
    if not (automatic_host_removal_ruleset := _load_automatic_host_removal_ruleset()):
        _LOGGER.debug("No cleanup rule configured: Terminating.")
        return  # small 'optimization'
    now = time.time()

    for hostname, check_mk_service_crit_since in _livestatus_query_local_candidates():
        _LOGGER.debug("Found '%s' to be CRIT since %0.2fs", hostname, check_mk_service_crit_since)
        if not (
            matches := list(
                analyze_host_rule_matches(
                    hostname, [automatic_host_removal_ruleset], debug=debug
                ).results.values()
            )[0]
        ):
            _LOGGER.debug("No matched rule: Skipping")
            continue

        # Unfortunately we don't get specific typing of the value out of analyze_host_rule_matches.
        # So reconstruct the original value to help mypy with typing.
        first_match = matches[0]
        _LOGGER.debug("Matching rule: %r", first_match)
        matched_value: (
            tuple[Literal["enabled"], _RemovalConditions] | tuple[Literal["disabled"], None]
        )
        match first_match:
            case ("enabled", {"checkmk_service_crit": int(crit)}):
                matched_value = ("enabled", _RemovalConditions({"checkmk_service_crit": crit}))
            case ("disabled", _):
                matched_value = ("disabled", None)
            case _:
                raise ValueError("Unexpected match")

        if _should_delete_host(
            rule_value=matched_value,
            check_mk_service_crit_for=now - check_mk_service_crit_since,
        ):
            _LOGGER.debug("Shall be removed")
            yield hostname
        else:
            _LOGGER.debug("Shall not be removed")


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
    checkmk_service_crit: int  # seconds


def _should_delete_host(
    *,
    rule_value: tuple[Literal["enabled"], _RemovalConditions] | tuple[Literal["disabled"], None],
    check_mk_service_crit_for: float,
) -> bool:
    # TODO: use a match statement once mypy can handle this
    if rule_value[0] == "enabled":
        return check_mk_service_crit_for >= rule_value[1]["checkmk_service_crit"]
    return False


def _activate_changes(sites: Collection[SiteId], *, debug: bool) -> None:
    _LOGGER_BACKGROUND_JOB.debug("Activating changes for %d site(s)", len(sites))

    # workaround until CMK-13093 is fixed
    folder_tree().invalidate_caches()
    manager = ActivateChangesManager()
    manager.load()
    with SuperUserContext():
        activation_id = manager.start(
            sites=list(sites),
            source="INTERNAL",
            activate_foreign=True,
            debug=debug,
        )
        _LOGGER_BACKGROUND_JOB.info("Activation %s started", activation_id)

        timeout = 60
        while manager.is_running() and timeout > 0:
            _LOGGER_BACKGROUND_JOB.info("Waiting for activation to finish...")
            time.sleep(1)
            timeout -= 1

        for site_id in sites:
            state = manager.get_site_state(site_id)
            if state and state["_state"] != "success":
                _LOGGER_BACKGROUND_JOB.error(
                    "Activation of site %s failed: %s", site_id, state.get("_status_details")
                )

        _LOGGER_BACKGROUND_JOB.info("Activation finished")


class AutomationHostsForAutoRemoval(AutomationCommand[None]):
    def command_name(self) -> str:
        return "hosts-for-auto-removal"

    def execute(self, api_request: None) -> str:
        return json.dumps(list(_hosts_to_be_removed_local(debug=active_config.debug)))

    def get_request(self) -> None:
        pass
