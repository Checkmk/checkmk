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
from contextlib import contextmanager
from enum import IntEnum
from pathlib import Path
from typing import Any

import pytest

from tests.testlib.common.repo import qa_test_data_path
from tests.testlib.common.utils import wait_until
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


def get_host_names(
    site: Site | None = None, dump_dir: Path | None = None, piggyback: bool = False
) -> list[str]:
    """Return the list of agent/snmp hosts via filesystem or site.openapi."""
    dump_dir = (dump_dir or config.dump_dir_integration) / ("piggyback" if piggyback else "")
    if site:
        hosts = [_ for _ in site.openapi.hosts.get_all() if _.get("id") not in (None, "", site.id)]
        agent_host_names = [_["id"] for _ in hosts if "tag_snmp_ds" not in _.get("attributes", {})]
        snmp_host_names = [_.get("id") for _ in hosts if "tag_snmp_ds" in _.get("attributes", {})]
    else:
        agent_host_names = []
        snmp_host_names = []
        if not dump_dir.exists():
            # need to skip here to abort the collection and return RC=5: "no tests collected"
            pytest.skip(f'Folder "{dump_dir}" not found; exiting!', allow_module_level=True)
        for dump_file_name in [
            _
            for _ in os.listdir(dump_dir)
            if (not _.startswith(".") and _ not in config.skipped_dumps)
            and os.path.isfile(os.path.join(dump_dir, _))
        ]:
            try:
                dump_file_path = dump_dir / dump_file_name
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
    return agent_host_names + snmp_host_names


def read_disk_dump(host_name: str, piggyback: bool = False) -> str:
    """Return the content of an agent dump from the dumps' folder."""
    dump_dir = str(config.dump_dir_integration) + ("/piggyback" if piggyback else "")
    dump_file_path = f"{dump_dir}/{host_name}"
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
        for dump_name in get_host_names(dump_dir=dump_dir):
            assert (
                run(
                    [
                        "cp",
                        "-f",
                        f"{dump_dir}/{dump_name}",
                        (
                            f"{walk_path}/{dump_name}"
                            if re.search(r"\bsnmp\b", dump_name)
                            else f"{dump_path}/{dump_name}"
                        ),
                    ],
                    sudo=True,
                ).returncode
                == 0
            )

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
        pending_checks = []
        for idx in range(3):
            # we have to schedule the checks multiple times (twice at least):
            # => once to get baseline data
            # => a second time to calculate differences
            # => a third time since some checks require it
            site.schedule_check(host_name, "Check_MK", 0, 60)
            pending_checks = site.openapi.services.get_host_services(host_name, pending=True)
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
    dump_path_repo = str(qa_test_data_path() / "plugins_integration/dumps/piggyback")
    assert (
        run(
            [
                "cp",
                "-f",
                f"{dump_path_repo}/{source_host_name}",
                f"{site.path(dump_path_site)}/{source_host_name}",
            ],
            sudo=True,
        ).returncode
        == 0
    )
    site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True, strict=False)

    logger.info("Running service discovery...")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(source_host_name)

    with _dcd_connector(site):
        pb_hosts_from_dump = read_piggyback_hosts_from_dump(
            read_disk_dump(source_host_name, piggyback=True)
        )
        try:
            execute_dcd_cycle(site, expected_pb_hosts=len(pb_hosts_from_dump))
            piggyback_hosts = get_piggyback_hosts(site, source_host_name)
            assert piggyback_hosts, f'No piggyback hosts found for source host "{source_host_name}"'

            hostnames = piggyback_hosts + [source_host_name]
            for hostname in hostnames:
                assert site.get_host_services(hostname)["Check_MK"].state == 0
                logger.info("Scheduling checks & checking for pending services...")
                pending_checks = []
                for idx in range(3):
                    # we have to schedule the checks multiple times (twice at least):
                    # => once to get baseline data
                    # => a second time to calculate differences
                    # => a third time since some checks require it
                    site.schedule_check(hostname, "Check_MK", 0, 60)
                    pending_checks = site.openapi.services.get_host_services(hostname, pending=True)
                    if idx > 0 and len(pending_checks) == 0:
                        break

                if pending_checks:
                    logger.info(
                        '%s pending service(s) found on host "%s": %s',
                        len(pending_checks),
                        hostname,
                        ",".join(
                            _.get("extensions", {}).get("description", _.get("id"))
                            for _ in pending_checks
                        ),
                    )

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
                assert not get_piggyback_hosts(site, source_host_name), (
                    "Piggyback hosts still found: %s" % piggyback_hosts
                )


def get_piggyback_hosts(site: Site, source_host: str) -> list[str]:
    return [_ for _ in site.openapi.hosts.get_all_names() if _ != source_host]


@contextmanager
def _dcd_connector(test_site_piggyback: Site) -> Iterator[None]:
    logger.info("Creating a DCD connection for piggyback hosts...")
    dcd_id = "dcd_connector"
    host_attributes = {
        "tag_snmp_ds": "no-snmp",
        "tag_agent": "no-agent",
        "tag_piggyback": "piggyback",
        "tag_address_family": "no-ip",
    }
    test_site_piggyback.openapi.dcd.create(
        dcd_id=dcd_id,
        title="DCD Connector for piggyback hosts",
        host_attributes=host_attributes,
        interval=dcd_interval,
        validity_period=60,
        max_cache_age=60,
        delete_hosts=True,
        no_deletion_time_after_init=60,
    )
    with test_site_piggyback.openapi.wait_for_completion(300, "get", "activate_changes"):
        test_site_piggyback.openapi.changes.activate(force_foreign_changes=True)
    try:
        yield
    finally:
        if not config.skip_cleanup:
            test_site_piggyback.openapi.dcd.delete(dcd_id)
            test_site_piggyback.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=True
            )


def execute_dcd_cycle(site: Site, expected_pb_hosts: int = 0) -> None:
    """Execute a DCD cycle and wait for its completion.

    Trigger a DCD cycle until:
    1) One batch that computes all expected PB hosts is completed;
    2) The last batch in the queue contains the expected number of PB hosts.

    This is needed to ensure that the DCD has processed all piggyback hosts and those hosts persist
    in the following batches.

    Args:
        site: The Site instance where the DCD cycle should be executed
        expected_pb_hosts: The number of piggyback hosts expected to be discovered
    """

    def _wait_for_hosts_in_batch() -> bool:
        site.run(["cmk-dcd", "--execute-cycle"])

        logger.info(
            "Waiting for DCD to compute the expected number of PB hosts.\nExpected PB hosts: %s",
            expected_pb_hosts,
        )
        all_batches_stdout = site.check_output(["cmk-dcd", "--batches"]).strip("\n").split("\n")
        logger.info("DCD batches:\n%s", "\n".join(all_batches_stdout[:]))

        # check if the last batch contains the expected number of PB hosts
        if f"{expected_pb_hosts} hosts" in all_batches_stdout[-1]:
            # check if there is at least one completed batch containing the expected number of PB
            # hosts
            for batch_stdout in all_batches_stdout:
                if all(string in batch_stdout for string in ["Done", f"{expected_pb_hosts} hosts"]):
                    return True
        return False

    max_count = 30
    interval = dcd_interval

    try:
        wait_until(
            _wait_for_hosts_in_batch,
            (max_count * interval) + 1,
            interval,
            "dcd: wait for hosts in DCD batch",
        )
    except TimeoutError as excp:
        excp.add_note(
            f"The expected number of piggyback hosts was not computed within {max_count} cycles."
        )


def read_piggyback_hosts_from_dump(dump: str) -> set[str]:
    """Read piggyback hosts from the agent dump.

    A piggyback host is defined by the pattern '<<<<host_name>>>>' within the agent dump.
    """
    piggyback_hosts: set[str] = set()
    pattern = r"<<<<(.*?)>>>>"
    matches = re.findall(pattern, dump)
    piggyback_hosts.update(matches)
    piggyback_hosts.discard("")  # '<<<<>>>>' pattern will match an empty string
    return piggyback_hosts
