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
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import yaml

from tests.testlib.site import Site
from tests.testlib.utils import execute

from tests.plugins_integration import constants

LOGGER = logging.getLogger(__name__)


def _apply_regexps(identifier: str, canon: dict, result: dict) -> None:
    """Apply regular expressions to the canon and result objects."""
    regexp_filepath = f"{os.path.dirname(__file__)}/regexp.yaml"
    if not os.path.exists(regexp_filepath):
        return
    with open(regexp_filepath, mode="r", encoding="utf-8") as regexp_file:
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
            LOGGER.debug("> Applying regexp: %s", pattern)
            if not canon.get(field_name):
                LOGGER.debug(
                    '> Field "%s" not found in canon "%s", skipping...', field_name, identifier
                )
                continue
            if not result.get(field_name):
                LOGGER.debug(
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
            for check in site.openapi.get_host_services(
                host_name, columns=constants.API_SERVICES_COLS
            )
            if len(constants.CHECK_NAMES) == 0
            or check["id"] in constants.CHECK_NAMES
            or any(re.fullmatch(pattern, check["id"]) for pattern in constants.CHECK_NAMES)
        }
    except json.decoder.JSONDecodeError as exc:
        raise ValueError(
            "Could not get valid check data! Make sure the site is running "
            "and the provided secret is correct!"
        ) from exc


def get_host_names(site: Optional[Site] = None) -> list[str]:
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
        for dump_file_name in [
            _ for _ in os.listdir(constants.DUMP_DIR_PATH) if not _.startswith(".")
        ]:
            try:
                dump_file_path = f"{constants.DUMP_DIR_PATH}/{dump_file_name}"
                with open(dump_file_path, mode="r", encoding="utf-8") as dump_file:
                    if dump_file.read(1) == ".":
                        snmp_host_names.append(dump_file_name)
                    else:
                        agent_host_names.append(dump_file_name)
            except OSError:
                LOGGER.error('Could not access dump file "%s"!', dump_file_name)
            except UnicodeDecodeError:
                LOGGER.error('Could not decode dump file "%s"!', dump_file_name)
    if "agent" in constants.DUMP_TYPES:
        host_names += agent_host_names
    if "snmp" in constants.DUMP_TYPES:
        host_names += snmp_host_names
    host_names = [
        _
        for _ in host_names
        if len(constants.HOST_NAMES) == 0
        or _ in constants.HOST_NAMES
        or any(re.fullmatch(pattern, _) for pattern in constants.HOST_NAMES)
    ]
    return host_names


def read_disk_dump(host_name: str) -> str:
    """Return the content of an agent dump from the dumps folder."""
    dump_file_path = f"{constants.DUMP_DIR_PATH}/{host_name}"
    with open(dump_file_path, mode="r", encoding="utf-8") as dump_file:
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
    check_file_name: str,
    result_data: dict[str, Any],
    output_dir: Path,
    update_mode: bool,
    apply_regexps: bool,
) -> bool:
    """Verify that the check result is matching the stored canon.

    Optionally update the stored canon if it does not match."""
    json_output_file_path = f"{constants.RESPONSE_DIR_PATH}/{check_file_name}.json"
    if os.path.exists(json_output_file_path):
        with open(json_output_file_path, mode="r", encoding="utf-8") as json_file:
            canon_data = json.load(json_file)
    else:
        if not update_mode:
            LOGGER.warning('Canon file "%s" not found!', json_output_file_path)
        canon_data = {}
    json_result_file_path = str(output_dir / f"{check_file_name}.result.json")
    with open(json_result_file_path, mode="w", encoding="utf-8") as json_file:
        json_file.write(f"{json.dumps(result_data, indent=4)}\n")

    if not update_mode:
        # ignore columns in the canon that are not supposed to be returned
        canon_data = {_: canon_data[_] for _ in canon_data if _ in constants.API_SERVICES_COLS}
    json_canon_file_path = str(output_dir / f"{check_file_name}.canon.json")
    if apply_regexps:
        _apply_regexps(check_file_name, canon_data, result_data)

    if result_data and canon_data == result_data:
        return True

    if update_mode:
        with open(json_output_file_path, mode="w", encoding="utf-8") as json_file:
            json_file.write(f"{json.dumps(result_data, indent=4)}\n")
        LOGGER.info('Canon file "%s" updated!', json_output_file_path)
        return True
    with open(json_canon_file_path, mode="w", encoding="utf-8") as json_file:
        json_file.write(f"{json.dumps(canon_data, indent=4)}\n")

    if result_data is None or len(result_data) == 0:
        LOGGER.error("%s: No data returned!", check_file_name)
    elif len(canon_data) != len(result_data):
        LOGGER.error("%s: Data length mismatch!", check_file_name)
    else:
        LOGGER.error("%s: Data mismatch!", check_file_name)

    LOGGER.error(
        execute(
            shlex.split(os.getenv("DIFF_CMD", "diff"))
            + [
                json_canon_file_path,
                json_result_file_path,
            ],
            check=False,
        ).stdout,
    )

    return False


def process_raw_data(site: Site, host_name: str) -> tuple[str, str]:
    """Return both the cmk dump and the disk dump."""
    disk_dump = read_disk_dump(host_name)
    dump_type = "snmp" if disk_dump[0] == "." else "agent"
    return disk_dump, read_cmk_dump(host_name, site, dump_type)


def process_check_output(
    site: Site, host_name: str, output_dir: Path, update_mode: bool, apply_regexps: bool
) -> bool:
    """Process the check output and either dump or compare it."""
    passed = True if update_mode else None
    LOGGER.info('> Processing agent host "%s"...', host_name)
    check_results = get_check_results(site, host_name)
    for check_id in sorted(check_results):
        LOGGER.debug('> Processing check id "%s"...', check_id)
        check_result = check_results[check_id]
        check_host_name = check_id.split(":", 1)[0]
        check_display_name = check_result.get("display_name", check_id.split(":", 1)[-1]).replace(
            f"_{site.id}_", "_SITE_"
        )
        check_safe_name = check_display_name.replace("$", "_").replace(" ", "_").replace("/", "#")
        check_file_name = f"{check_host_name}.{check_safe_name}"

        LOGGER.debug('> Verifying check id "%s"...', check_id)
        if _verify_check_result(
            check_file_name,
            check_result.get("extensions", {}),
            output_dir,
            update_mode,
            apply_regexps,
        ):
            if passed is None:
                passed = True
            continue
        passed = False

    return passed is True


@contextmanager
def setup_host(site: Site, host_name: str) -> Iterator:
    LOGGER.info('Creating host "%s"...', host_name)
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

    LOGGER.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    LOGGER.info("Running service discovery...")
    site.openapi.discover_services_and_wait_for_completion(host_name)
    site.openapi.bulk_discover_services([host_name], bulk_size=10, wait_for_completion=True)

    LOGGER.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    LOGGER.info("Scheduling checks & checking for pending services...")
    for idx in range(3):
        # we have to schedule the checks multiple times (twice at least):
        # => once to get baseline data
        # => a second time to calculate differences
        # => a third time since some checks require it
        site.schedule_check(host_name, "Check_MK", 0, 60)
        pending_checks = site.openapi.get_host_services(host_name, pending=True)
        if idx > 0 and len(pending_checks) == 0:
            continue

    if len(pending_checks) > 0:
        LOGGER.info(
            '%s pending service(s) found on host "%s": %s',
            len(pending_checks),
            host_name,
            ",".join(
                _.get("extensions", {}).get("description", _.get("id")) for _ in pending_checks
            ),
        )

    yield

    LOGGER.info('Deleting host "%s"...', host_name)
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
    LOGGER.info("Bulk-creating %s hosts...", len(host_entries))
    site.openapi.bulk_create_hosts(
        host_entries,
        bake_agent=False,
        ignore_existing=True,
    )

    LOGGER.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    LOGGER.info("Running service discovery...")
    site.openapi.bulk_discover_services(host_names, bulk_size=10, wait_for_completion=True)

    LOGGER.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()

    LOGGER.info("Checking for pending services...")
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
        LOGGER.info(
            '%s pending service(s) found on host "%s": %s',
            len(pending_checks[host_name]),
            host_name,
            ",".join(
                _.get("extensions", {}).get("description", _.get("id"))
                for _ in pending_checks[host_name]
            ),
        )


def cleanup_hosts(site: Site, host_names: list[str]) -> None:
    LOGGER.info("Bulk-deleting %s hosts...", len(host_names))
    site.openapi.bulk_delete_hosts(host_names)

    LOGGER.info("Activating changes & reloading core...")
    site.activate_changes_and_wait_for_core_reload()
