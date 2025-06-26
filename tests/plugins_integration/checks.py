#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os
import re
import shlex
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from enum import IntEnum
from pathlib import Path
from typing import Any

import pytest

from tests.testlib.agent_dumps import copy_dumps, read_disk_dump, read_piggyback_hosts_from_dump
from tests.testlib.common.repo import qa_test_data_path
from tests.testlib.dcd import dcd_connector, execute_dcd_cycle
from tests.testlib.site import Site
from tests.testlib.utils import run

logger = logging.getLogger(__name__)
dump_path_site = Path("var/check_mk/dumps")
dcd_interval = 5  # seconds


class CheckModes(IntEnum):
    DEFAULT = 0
    ADD = 1
    UPDATE = 2


class CheckConfig:
    def __init__(
        self,
        mode: CheckModes = CheckModes.DEFAULT,
        skip_cleanup: bool = False,
        data_dir_integration: Path | None = None,
        dump_dir_integration: Path | None = None,
        response_dir_integration: Path | None = None,
        data_dir_siteless: Path | None = None,
        dump_dir_siteless: Path | None = None,
        response_dir_siteless: str | None = None,
        diff_dir: Path | None = None,
        check_names: list[str] | None = None,
        api_services_cols: list[str] | None = None,
    ) -> None:
        self.skipped_dumps: list[str] = []
        self.skipped_checks: list[str] = []

        self.mode = mode
        self.skip_cleanup = skip_cleanup
        self.data_dir_integration = data_dir_integration or (
            qa_test_data_path() / "plugins_integration"
        )
        self.dump_dir_integration = dump_dir_integration or (self.data_dir_integration / "dumps")
        self.response_dir_integration = response_dir_integration or (
            self.data_dir_integration / "responses"
        )

        self.data_dir_siteless = data_dir_siteless or (qa_test_data_path() / "plugins_siteless")
        self.dump_dir_siteless = dump_dir_siteless or (self.data_dir_siteless / "agent_data")
        self.response_dir_siteless = response_dir_siteless or (self.data_dir_siteless / "responses")

        self.diff_dir = diff_dir or Path(os.getenv("DIFF_DIR", "/tmp"))
        self.check_names = check_names or [
            _.strip() for _ in str(os.getenv("CHECK_NAMES", "")).split(",") if _.strip()
        ]

        # these SERVICES table columns will be returned via the get_host_services() openapi call
        # NOTE: extending this list will require an update of the check output (--update-checks)
        self.api_services_cols = api_services_cols or [
            "host_name",
            "check_command",
            "check_command_expanded",
            "check_options",
            "check_period",
            "check_type",
            "description",
            "display_name",
            "has_been_checked",
            "labels",
            "state",
            "state_type",
            "tags",
        ]

        # log defined values
        for attr in (attrs := vars(self)):
            logger.info("%s=%s", attr.upper(), attrs[attr])


config = CheckConfig()


def get_check_results(site: Site, host_name: str) -> dict[str, Any]:
    """Return the current check results from the API."""
    try:
        return {
            check["id"]: check
            for check in site.openapi.services.get_host_services(
                host_name,
                columns=(config.api_services_cols or []) + ["plugin_output"],
                pending=False,
            )
            if not config.check_names
            or check["id"] in config.check_names
            or check["id"].split(":", 1)[-1] in config.check_names
            or any(re.fullmatch(pattern, check["id"]) for pattern in config.check_names)
        }
    except json.decoder.JSONDecodeError as exc:
        raise ValueError(
            "Could not get valid check data! Make sure the site is running "
            "and the provided secret is correct!"
        ) from exc


def _verify_check_result(
    check_id: str,
    canon_data: dict[str, Any],
    result_data: dict[str, Any],
    output_dir: Path,
    mode: CheckModes,
) -> tuple[bool, str]:
    """Verify that the check result is matching the stored canon.

    Optionally update the stored canon if it does not match."""
    if mode == CheckModes.DEFAULT and not canon_data:
        logger.error("[%s] Canon not found!", check_id)
        return False, ""

    check_output = str(result_data.pop("plugin_output", ""))

    safe_name = check_id.replace("$", "_").replace(" ", "_").replace("/", "#")
    with open(
        json_result_file_path := str(output_dir / f"{safe_name}.result.json"),
        mode="w",
        encoding="utf-8",
    ) as json_file:
        json.dump(result_data, json_file, indent=4, sort_keys=True)

    # ignore columns in the canon that are not supposed to be returned
    canon_data = {_: canon_data[_] for _ in canon_data if _ in (config.api_services_cols or [])}

    if result_data and canon_data == result_data:
        # if the canon was just added or matches the result, there is nothing else to do
        return True, ""

    logger.error("[%s] Plugin output: %s", check_id, check_output)

    with open(
        json_canon_file_path := str(output_dir / f"{safe_name}.canon.json"),
        mode="w",
        encoding="utf-8",
    ) as json_file:
        json.dump(canon_data, json_file, indent=4, sort_keys=True)

    if not result_data:
        logger.error("[%s] No data returned!", check_id)
        return False, ""

    diff = run(
        shlex.split(os.getenv("DIFF_CMD", "diff"))
        + [
            json_canon_file_path,
            json_result_file_path,
        ],
        check=False,
    ).stdout

    if mode != CheckModes.UPDATE:
        if len(canon_data) != len(result_data):
            logger.error("[%s] Invalid field count! Data mismatch:\n%s", check_id, diff)
        else:
            logger.error("[%s] Data mismatch:\n%s", check_id, diff)

    return False, diff


def process_check_output(
    site: Site,
    host_name: str,
    output_dir: Path,
) -> dict[str, str]:
    """Process the check output and either dump or compare it."""
    if host_name in config.skipped_dumps:
        pytest.skip(reason=f"{host_name} dumps currently skipped.")

    logger.info('> Processing agent host "%s"...', host_name)
    diffs = {}
    response_path = f"{config.response_dir_integration}/{host_name}.json"

    if os.path.exists(response_path):
        with open(response_path, encoding="utf-8") as json_file:
            check_canons = json.load(json_file)
    else:
        check_canons = {}

    passed = None
    check_results = {
        _: item.get("extensions") for _, item in get_check_results(site, host_name).items()
    }
    for check_id, results in check_results.items():
        if check_id in (config.skipped_checks or []):
            logger.info("Check %s currently skipped", check_id)
            passed = True
            continue

        logger.debug('> Processing check id "%s"...', check_id)
        if config.mode == CheckModes.ADD and not check_canons.get(check_id):
            check_canons[check_id] = results
            logger.info("[%s] Canon added!", check_id)

        logger.debug('> Verifying check id "%s"...', check_id)
        check_success, diff = _verify_check_result(
            check_id,
            check_canons.get(check_id, {}),
            results,
            output_dir,
            config.mode,
        )
        if config.mode == CheckModes.UPDATE and diff:
            check_canons[check_id] = results
            logger.info("[%s] Canon updated!", check_id)
            passed = True
            continue
        if check_success:
            if passed is None:
                passed = True
            continue

        passed = False
        diffs[check_id] = diff

    if diffs:
        os.makedirs(config.diff_dir, exist_ok=True)
        with open(
            f"{config.diff_dir}/{host_name}.json",
            mode="a",
            encoding="utf-8",
        ) as json_file:
            json.dump(diffs, json_file, indent=4, sort_keys=True)

    if config.mode != CheckModes.DEFAULT:
        with open(
            response_path,
            mode="w",
            encoding="utf-8",
        ) as json_file:
            json.dump(check_canons, json_file, indent=4, sort_keys=True)

    return diffs


def setup_site(site: Site, dump_path: Path, dump_dirs: Sequence[Path] | None = None) -> None:
    dump_dirs = dump_dirs or [config.dump_dir_integration]
    # NOTE: the snmpwalks folder cannot be changed!
    walk_path = site.path("var/check_mk/snmpwalks")
    # create dump folder in the test site
    logger.info('Creating folder "%s"...', dump_path)
    _ = site.run(["mkdir", "-p", dump_path.as_posix()])

    logger.info("Injecting agent-output...")
    for dump_dir in dump_dirs:
        copy_dumps(site, dump_dir, dump_path, "agent-")
        with suppress(subprocess.CalledProcessError):
            # there may be no SNMP walks in the source folder, which is fine
            copy_dumps(site, dump_dir, walk_path, "snmp-")

    for dump_type in ["agent", "snmp"]:
        host_folder = f"/{dump_type}"
        if site.openapi.folders.get(host_folder):
            logger.info('Host folder "%s" already exists!', host_folder)
        else:
            logger.info('Creating host folder "%s"...', host_folder)
            site.openapi.folders.create(host_folder)
        ruleset_name = "usewalk_hosts" if dump_type == "snmp" else "datasource_programs"
        logger.info('Creating rule "%s"...', ruleset_name)
        site.openapi.rules.create(
            ruleset_name=ruleset_name,
            value=(True if dump_type == "snmp" else f"cat {dump_path}/<HOST>"),
            folder=host_folder,
        )
        logger.info('Rule "%s" created!', ruleset_name)
    site.openapi.changes.activate_and_wait_for_completion()


@contextmanager
def setup_host(
    site: Site,
    host_name: str,
    skip_cleanup: bool = False,
    management_board: bool = False,
) -> Iterator:
    logger.info('Creating host "%s"...', host_name)
    host_attributes = {
        "ipaddress": "127.0.0.1",
        "tag_agent": ("no-agent" if "snmp" in host_name else "cmk-agent"),
    }

    if management_board:
        host_attributes.update(
            {
                "tag_agent": "no-agent",
                "management_protocol": "snmp",
            }
        )
    elif "snmp" in host_name:
        host_attributes["tag_snmp_ds"] = "snmp-v2"

    site.openapi.hosts.create(
        hostname=host_name,
        folder="/snmp" if "snmp" in host_name else "/agent",
        attributes=host_attributes,
        bake_agent=False,
    )

    try:
        site.openapi.changes.activate_and_wait_for_completion(strict=False)

        logger.info("Running service discovery...")
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
        site.openapi.changes.activate_and_wait_for_completion()

        logger.info("Scheduling checks & checking for pending services...")
        site.reschedule_services(host_name, 3, strict=False)
        yield
    finally:
        if not (config.skip_cleanup or skip_cleanup):
            logger.info('Deleting host "%s"...', host_name)
            site.openapi.hosts.delete(host_name)
            site.activate_changes_and_wait_for_core_reload()


@contextmanager
def setup_source_host_piggyback(
    site: Site, source_host_name: str, folder_name: str = "/"
) -> Iterator:
    logger.info('Creating source host "%s"...', source_host_name)
    host_attributes = {"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"}
    site.openapi.hosts.create(
        hostname=source_host_name,
        folder=folder_name,
        attributes=host_attributes,
        bake_agent=False,
    )

    logger.info("Injecting agent-output...")
    dump_path_repo = qa_test_data_path() / "plugins_integration/dumps/piggyback"
    copy_dumps(site, dump_path_repo, site.path(dump_path_site), source_filename=source_host_name)
    site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True, strict=False)

    logger.info("Running service discovery...")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(source_host_name)

    with dcd_connector(site, dcd_interval, auto_cleanup=not config.skip_cleanup):
        pb_hosts_from_dump = read_piggyback_hosts_from_dump(
            read_disk_dump(source_host_name, config.dump_dir_integration / "piggyback")
        )
        piggyback_hosts = None
        try:
            execute_dcd_cycle(site, expected_pb_hosts=len(pb_hosts_from_dump))
            piggyback_hosts = site.openapi.hosts.get_all_names([source_host_name])
            assert piggyback_hosts, f'No piggyback hosts found for source host "{source_host_name}"'

            for host_name in piggyback_hosts + [source_host_name]:
                site.reschedule_services(host_name, 3, strict=False)

            yield
        finally:
            if not config.skip_cleanup:
                logger.info('Deleting source host "%s"...', source_host_name)
                site.openapi.hosts.delete(source_host_name)

                site.run(["rm", "-f", f"{dump_path_site}/{source_host_name}"])

                site.openapi.changes.activate_and_wait_for_completion(
                    force_foreign_changes=True, strict=False
                )
                execute_dcd_cycle(site, expected_pb_hosts=0)
                assert not site.openapi.hosts.get_all_names([source_host_name]), (
                    "Piggyback hosts still found: %s" % piggyback_hosts
                )
