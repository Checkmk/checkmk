#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os
import re
import shlex
from pathlib import Path
from typing import Any, Optional

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
    with open(regexp_filepath, "r", encoding="utf-8") as regexp_file:
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
        }
    except json.decoder.JSONDecodeError as exc:
        raise ValueError(
            "Could not get valid check data! Make sure the site is running "
            "and the provided secret is correct!"
        ) from exc


def get_host_names(site: Optional[Site] = None) -> list[str]:
    """Return the list of hosts via filesystem or site.openapi."""
    if site:
        host_names = [
            host.get("id")
            for host in site.openapi.get_hosts()
            if host.get("id") not in (None, "", site.id)
        ]
    else:
        host_names = [_ for _ in os.listdir(constants.DUMP_DIR_PATH) if not _.startswith(".")]
    snmp_host_names = [host_names.pop(i) for i, _ in enumerate(host_names) if "snmp" in _]
    if "agent" not in constants.DUMP_TYPES:
        host_names = []
    if "snmp" in constants.DUMP_TYPES:
        host_names += snmp_host_names
    return [
        _
        for _ in host_names
        if len(constants.HOST_NAMES) == 0
        or _ in constants.HOST_NAMES
        or any(re.fullmatch(pattern, _) for pattern in constants.HOST_NAMES)
    ]


def get_check_names(site: Optional[Site] = None) -> list[str]:
    """Return the list of checks via filesystem or site.openapi."""
    if site:
        check_names = []
        for host_name in get_host_names(site):
            check_names += list(check["id"] for check in site.openapi.get_host_services(host_name))
    else:
        check_names = [_ for _ in os.listdir(constants.RESPONSE_DIR_PATH) if not _.startswith(".")]
    return [_ for _ in check_names if len(constants.CHECK_NAMES) == 0 or _ in constants.CHECK_NAMES]


def _verify_check_result(
    check_file_name: str,
    result_data: dict[str, Any],
    output_dir: Path,
    update_mode: bool,
) -> bool:
    """Verify that the check result is matching the stored canon.

    Optionally update the stored canon if it does not match."""
    json_output_file_path = f"{constants.RESPONSE_DIR_PATH}/{check_file_name}.json"
    if os.path.exists(json_output_file_path):
        with open(json_output_file_path, "r", encoding="utf-8") as json_file:
            canon_data = json.load(json_file)
    else:
        LOGGER.warning('Canon file "%s" not found!', json_output_file_path)
        canon_data = {}
    json_result_file_path = str(output_dir / f"{check_file_name}.result.json")
    with open(json_result_file_path, "w", encoding="utf-8") as json_file:
        json_file.write(f"{json.dumps(result_data, indent=4)}\n")

    if not update_mode:
        # ignore columns in the canon that are not supposed to be returned
        canon_data = {_: canon_data[_] for _ in canon_data if _ in constants.API_SERVICES_COLS}
    json_canon_file_path = str(output_dir / f"{check_file_name}.canon.json")
    _apply_regexps(check_file_name, canon_data, result_data)

    if result_data and canon_data == result_data:
        return True

    if update_mode:
        with open(json_output_file_path, "w", encoding="utf-8") as json_file:
            json_file.write(f"{json.dumps(result_data, indent=4)}\n")
        return True
    with open(json_canon_file_path, "w", encoding="utf-8") as json_file:
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


def process_check_output(site: Site, host_name: str, output_dir: Path, update_mode: bool) -> bool:
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
            check_file_name, check_result.get("extensions", {}), output_dir, update_mode
        ):
            if passed is None:
                passed = True
            continue
        passed = False

    return passed is True
