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
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.testlib.repo import qa_test_data_path
from tests.testlib.site import Site
from tests.testlib.utils import run

logger = logging.getLogger(__name__)


@dataclass
class SkippedDumps:
    SKIPPED_DUMPS = []  # type: ignore


@dataclass
class SkippedChecks:
    SKIPPED_CHECKS = []  # type: ignore


class CheckModes(IntEnum):
    DEFAULT = 0
    ADD = 1
    UPDATE = 2


@dataclass
class CheckConfig:
    mode: CheckModes = CheckModes.DEFAULT
    skip_masking: bool = False
    skip_cleanup: bool = False
    dump_types: list[str] | None = None
    data_dir: str | None = None
    dump_dir: str | None = None
    response_dir: str | None = None
    diff_dir: str | None = None
    host_names: list[str] | None = None
    check_names: list[str] | None = None
    api_services_cols: list | None = None
    piggyback: bool = False

    def load(self):
        data_dir_default = str(qa_test_data_path() / "plugins_integration")
        dump_dir_default = f"{data_dir_default}/dumps" + ("/piggyback" if self.piggyback else "")
        response_dir_default = f"{data_dir_default}/responses" + (
            "/piggyback" if self.piggyback else ""
        )

        self.data_dir = str(self.data_dir or os.getenv("DATA_DIR", data_dir_default))
        self.dump_dir = str(self.dump_dir or os.getenv("DUMP_DIR", dump_dir_default))
        self.response_dir = str(
            self.response_dir or os.getenv("RESPONSE_DIR", response_dir_default)
        )
        self.diff_dir = str(self.diff_dir or os.getenv("DIFF_DIR", "/tmp"))
        self.host_names = (
            [_.strip() for _ in str(os.getenv("HOST_NAMES", "")).split(",") if _.strip()]
            if not self.host_names
            else self.host_names
        )
        self.check_names = (
            [_.strip() for _ in str(os.getenv("CHECK_NAMES", "")).split(",") if _.strip()]
            if not self.check_names
            else self.check_names
        )
        self.dump_types = (
            [_.strip() for _ in str(os.getenv("DUMP_TYPES", "agent,snmp")).split(",") if _.strip()]
            if not self.dump_types
            else self.dump_types
        )

        # these SERVICES table columns will be returned via the get_host_services() openapi call
        # NOTE: extending this list will require an update of the check output (--update-checks)
        self.api_services_cols = [
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
            "plugin_output",
            "state",
            "state_type",
            "tags",
        ]

        # log defined values
        for attr in (attrs := vars(self)):
            logger.info("%s=%s", attr.upper(), attrs[attr])


config = CheckConfig()


def _apply_regexps(identifier: str, canon: dict, result: dict) -> None:
    """Apply regular expressions to the canon and result objects."""
    regexp_filepath = f"{config.data_dir}/regexp.yaml"
    if not os.path.exists(regexp_filepath):
        return
    with open(regexp_filepath, encoding="utf-8") as regexp_file:
        all_patterns = yaml.safe_load(regexp_file)
    # global regexps
    patterns = all_patterns.get("*", {})
    # pattern matches
    patterns.update(
        next((item for name, item in all_patterns.items() if re.match(name, identifier)), {})
    )
    # exact matches
    patterns.update(all_patterns.get(identifier, {}))

    for pattern_group in all_patterns:
        if not (pattern_group == identifier or re.match(pattern_group, identifier)):
            continue
        patterns = all_patterns[pattern_group]

        for field_name in patterns:
            pattern = patterns[field_name]
            logger.debug("> Applying regexp: %s", pattern)
            if not canon.get(field_name):
                logger.debug(
                    '> Field "%s" not found in canon "%s", skipping...', field_name, identifier
                )
                continue
            if not result.get(field_name):
                logger.debug(
                    '> Field "%s" not found in result "%s", skipping...', field_name, identifier
                )
                continue
            if match := re.search(pattern, result[field_name]):
                canon[field_name] = re.sub(
                    pattern,
                    match.group(),
                    canon[field_name],
                )


def get_check_results(site: Site, host_name: str) -> dict[str, Any]:
    """Return the current check results from the API."""
    try:
        return {
            check["id"]: check
            for check in site.openapi.get_host_services(host_name, columns=config.api_services_cols)
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


def get_host_names(site: Site | None = None) -> list[str]:
    """Return the list of agent/snmp hosts via filesystem or site.openapi."""
    host_names = []
    if site:
        hosts = [_ for _ in site.openapi.get_hosts() if _.get("id") not in (None, "", site.id)]
        agent_host_names = [
            _.get("id") for _ in hosts if "tag_snmp_ds" not in _.get("attributes", {})
        ]
        snmp_host_names = [_.get("id") for _ in hosts if "tag_snmp_ds" in _.get("attributes", {})]
    else:
        agent_host_names = []
        snmp_host_names = []
        if not (config.dump_dir and os.path.exists(config.dump_dir)):
            # need to skip here to abort the collection and return RC=5: "no tests collected"
            pytest.skip(f'Folder "{config.dump_dir}" not found; exiting!', allow_module_level=True)
        for dump_file_name in [
            _
            for _ in os.listdir(config.dump_dir)
            if (not _.startswith(".") and _ not in SkippedDumps.SKIPPED_DUMPS)
            and os.path.isfile(os.path.join(config.dump_dir, _))
        ]:
            try:
                dump_file_path = f"{config.dump_dir}/{dump_file_name}"
                with open(dump_file_path, encoding="utf-8") as dump_file:
                    if re.match(r"^snmp-", dump_file_name) and dump_file.read(1) == ".":
                        snmp_host_names.append(dump_file_name)
                    elif re.match(r"^agent-\d+\.\d+\.\d+\w*\d*-", dump_file_name):
                        agent_host_names.append(dump_file_name)
                    else:
                        raise Exception(
                            f"A dump file name should start either with 'agent-X.X.XpX-' or with "
                            f"'snmp-', where X.X.XpX defines the agent version used."
                            f"This is not the case for {dump_file_name}"
                        )
            except OSError:
                logger.error('Could not access dump file "%s"!', dump_file_name)
            except UnicodeDecodeError:
                logger.error('Could not decode dump file "%s"!', dump_file_name)
    if not config.dump_types or "agent" in config.dump_types:
        host_names += agent_host_names
    if not config.dump_types or "snmp" in config.dump_types:
        host_names += snmp_host_names
    host_names = [
        _
        for _ in host_names
        if not config.host_names
        or _ in config.host_names
        or any(re.fullmatch(pattern, _) for pattern in config.host_names)
    ]
    return host_names


def read_disk_dump(host_name: str) -> str:
    """Return the content of an agent dump from the dumps folder."""
    dump_file_path = f"{config.dump_dir}/{host_name}"
    with open(dump_file_path, encoding="utf-8") as dump_file:
        return dump_file.read()


def read_cmk_dump(host_name: str, site: Site, dump_type: str) -> str:
    """Return the current agent or snmp dump via cmk."""
    args = ["cmk", "--snmptranslate" if dump_type == "snmp" else "-d", host_name]
    cmk_dump, _ = site.execute(
        args,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ).communicate()
    if dump_type == "snmp":
        cmk_dump = "\n".join([_.split("-->")[0].strip() for _ in str(cmk_dump).splitlines()])

    return cmk_dump


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

    safe_name = check_id.replace("$", "_").replace(" ", "_").replace("/", "#")
    with open(
        json_result_file_path := str(output_dir / f"{safe_name}.result.json"),
        mode="w",
        encoding="utf-8",
    ) as json_file:
        json.dump(result_data, json_file, indent=4, sort_keys=True)

    if mode != CheckModes.UPDATE:
        # ignore columns in the canon that are not supposed to be returned
        canon_data = {_: canon_data[_] for _ in canon_data if _ in config.api_services_cols}  # type: ignore

    if not config.skip_masking:
        _apply_regexps(check_id, canon_data, result_data)

    if result_data and canon_data == result_data:
        # if the canon was just added or matches the result, there is nothing else to do
        return True, ""

    with open(
        json_canon_file_path := str(output_dir / f"{safe_name}.canon.json"),
        mode="w",
        encoding="utf-8",
    ) as json_file:
        json.dump(canon_data, json_file, indent=4, sort_keys=True)

    if result_data is None or len(result_data) == 0:
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


def process_raw_data(site: Site, host_name: str) -> tuple[str, str]:
    """Return both the cmk dump and the disk dump."""
    disk_dump = read_disk_dump(host_name)
    dump_type = "snmp" if disk_dump[0] == "." else "agent"
    return disk_dump, read_cmk_dump(host_name, site, dump_type)


def process_check_output(
    site: Site,
    host_name: str,
    output_dir: Path,
) -> dict[str, str]:
    """Process the check output and either dump or compare it."""
    if host_name in SkippedDumps.SKIPPED_DUMPS:
        pytest.skip(reason=f"{host_name} dumps currently skipped.")

    logger.info('> Processing agent host "%s"...', host_name)
    diffs = {}

    if os.path.exists(f"{config.response_dir}/{host_name}.json"):
        with open(
            f"{config.response_dir}/{host_name}.json",
            encoding="utf-8",
        ) as json_file:
            check_canons = json.load(json_file)
    else:
        check_canons = {}

    passed = None
    check_results = {
        _: item.get("extensions") for _, item in get_check_results(site, host_name).items()
    }
    for check_id in check_results:
        if check_id in SkippedChecks.SKIPPED_CHECKS:
            logger.info("Check %s currently skipped", check_id)
            passed = True
            continue

        logger.debug('> Processing check id "%s"...', check_id)
        if config.mode == CheckModes.ADD and not check_canons.get(check_id):
            check_canons[check_id] = check_results[check_id]
            logger.info("[%s] Canon added!", check_id)

        logger.debug('> Verifying check id "%s"...', check_id)
        check_success, diff = _verify_check_result(
            check_id,
            check_canons.get(check_id, {}),
            check_results[check_id],
            output_dir,
            config.mode,
        )
        if config.mode == CheckModes.UPDATE and diff:
            check_canons[check_id] = check_results[check_id]
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
        os.makedirs(config.diff_dir, exist_ok=True)  # type: ignore
        with open(
            f"{config.diff_dir}/{host_name}.json",
            mode="a",
            encoding="utf-8",
        ) as json_file:
            json.dump(diffs, json_file, indent=4, sort_keys=True)

    if config.mode != CheckModes.DEFAULT:
        with open(
            f"{config.response_dir}/{host_name}.json",
            mode="w",
            encoding="utf-8",
        ) as json_file:
            json.dump(check_canons, json_file, indent=4, sort_keys=True)

    return diffs


def setup_site(site: Site, dump_path: str) -> None:
    # NOTE: the snmpwalks folder cannot be changed!
    walk_path = site.path("var/check_mk/snmpwalks")
    # create dump folder in the test site
    logger.info('Creating folder "%s"...', dump_path)
    rc = site.execute(["mkdir", "-p", dump_path]).wait()
    assert rc == 0

    logger.info("Injecting agent-output...")
    for dump_name in get_host_names():
        assert (
            run(
                [
                    "sudo",
                    "cp",
                    "-f",
                    f"{config.dump_dir}/{dump_name}",
                    (
                        f"{walk_path}/{dump_name}"
                        if re.search(r"\bsnmp\b", dump_name)
                        else f"{dump_path}/{dump_name}"
                    ),
                ]
            ).returncode
            == 0
        )

    for dump_type in config.dump_types:  # type: ignore
        host_folder = f"/{dump_type}"
        if site.openapi.get_folder(host_folder):
            logger.info('Host folder "%s" already exists!', host_folder)
        else:
            logger.info('Creating host folder "%s"...', host_folder)
            site.openapi.create_folder(host_folder)
        ruleset_name = "usewalk_hosts" if dump_type == "snmp" else "datasource_programs"
        logger.info('Creating rule "%s"...', ruleset_name)
        site.openapi.create_rule(
            ruleset_name=ruleset_name,
            value=(True if dump_type == "snmp" else f"cat {dump_path}/<HOST>"),
            folder=host_folder,
        )
        logger.info('Rule "%s" created!', ruleset_name)


@contextmanager
def setup_host(site: Site, host_name: str, skip_cleanup: bool = False) -> Iterator:
    logger.info('Creating host "%s"...', host_name)
    host_attributes = {
        "ipaddress": "127.0.0.1",
        "tag_agent": ("no-agent" if "snmp" in host_name else "cmk-agent"),
    }
    if "snmp" in host_name:
        host_attributes["tag_snmp_ds"] = "snmp-v2"
    site.openapi.create_host(
        hostname=host_name,
        folder="/snmp" if "snmp" in host_name else "/agent",
        attributes=host_attributes,
        bake_agent=False,
    )

    logger.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    logger.info("Running service discovery...")
    site.openapi.discover_services_and_wait_for_completion(host_name)

    logger.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    if config.piggyback:
        _wait_for_piggyback_hosts(site, main_host=host_name)
        count = 0
        while (n_pending_changes := len(site.openapi.pending_changes([site.id]))) > 0 and count < 3:
            site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
            count += 1
        assert n_pending_changes == 0, "Pending changes found!"

    logger.info("Scheduling checks & checking for pending services...")
    pending_checks = []
    for idx in range(3):
        # we have to schedule the checks multiple times (twice at least):
        # => once to get baseline data
        # => a second time to calculate differences
        # => a third time since some checks require it
        site.schedule_check(host_name, "Check_MK", 0, 60)
        pending_checks = site.openapi.get_host_services(host_name, pending=True)
        if idx > 0 and len(pending_checks) == 0:
            break

    if pending_checks:
        logger.info(
            '%s pending service(s) found on host "%s": %s',
            len(pending_checks),
            host_name,
            ",".join(
                _.get("extensions", {}).get("description", _.get("id")) for _ in pending_checks
            ),
        )

    try:
        yield
    finally:
        if not (config.skip_cleanup or skip_cleanup):
            logger.info('Deleting host "%s"...', host_name)
            site.openapi.delete_host(host_name)


def setup_hosts(site: Site, host_names: list[str]) -> None:
    agent_host_names = [_ for _ in host_names if "snmp" not in _]
    snmp_host_names = [_ for _ in host_names if "snmp" in _]
    host_entries = [
        {
            "host_name": host_name,
            "folder": "/agent",
            "attributes": {
                "ipaddress": "127.0.0.1",
                "tag_agent": "cmk-agent",
            },
        }
        for host_name in agent_host_names
    ] + [
        {
            "host_name": host_name,
            "folder": "/snmp",
            "attributes": {
                "ipaddress": "127.0.0.1",
                "tag_agent": "no-agent",
                "tag_snmp_ds": "snmp-v2",
            },
        }
        for host_name in snmp_host_names
    ]
    logger.info("Bulk-creating %s hosts...", len(host_entries))
    site.openapi.bulk_create_hosts(
        host_entries,
        bake_agent=False,
        ignore_existing=True,
    )

    logger.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    logger.info("Running service discovery...")
    site.openapi.bulk_discover_services_and_wait_for_completion(host_names, bulk_size=10)

    logger.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    logger.info("Checking for pending services...")
    pending_checks = {_: site.openapi.get_host_services(_, pending=True) for _ in host_names}
    for idx in range(3):
        # we have to schedule the checks multiple times (twice at least):
        # => once to get baseline data
        # => a second time to calculate differences
        # => a third time since some checks require it
        for host_name in list(pending_checks.keys())[:]:
            site.schedule_check(host_name, "Check_MK", 0, 60)
            pending_checks[host_name] = site.openapi.get_host_services(host_name, pending=True)
            if idx > 0 and len(pending_checks[host_name]) == 0:
                pending_checks.pop(host_name, None)
                continue

    for host_name in pending_checks:
        logger.info(
            '%s pending service(s) found on host "%s": %s',
            len(pending_checks[host_name]),
            host_name,
            ",".join(
                _.get("extensions", {}).get("description", _.get("id"))
                for _ in pending_checks[host_name]
            ),
        )


def cleanup_hosts(site: Site, host_names: list[str]) -> None:
    logger.info("Bulk-deleting %s hosts...", len(host_names))
    site.openapi.bulk_delete_hosts(host_names)

    logger.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()


def _get_piggyback_hosts(site: Site, main_host: str) -> list[str]:
    return [_.get("id") for _ in site.openapi.get_hosts() if _.get("id") != main_host]


def _wait_for_piggyback_hosts(
    site: Site, main_host: str, max_count: int = 10, sleep_time: float = 1, strict: bool = True
) -> None:
    count = 0
    while not (piggyback_hosts := _get_piggyback_hosts(site, main_host)) and count < max_count:
        logger.info("Waiting for piggyback hosts to be created...")
        time.sleep(sleep_time)
        count += 1
    if strict:
        assert piggyback_hosts, "No piggyback hosts found."
