#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os
import re
import typing
from pathlib import Path

import requests
import yaml

from tests.testlib.site import Site

from . import constants
from .conftest import run_cmd

LOGGER = logging.getLogger(__name__)


def apply_regexps(identifier: str, canon: dict, result: dict) -> None:
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
    for field_name in patterns:
        pattern = patterns[field_name]
        LOGGER.debug("> Applying regexp: %s", pattern)
        match = re.search(pattern, result[field_name])
        if match:
            canon[field_name] = re.sub(
                pattern,
                match.group(),
                canon[field_name],
            )


def api_get(site: Site, request_path: str) -> requests.Response:
    """Executes an API "get" request and returns the response."""
    session = requests.Session()
    session.headers["authorization"] = f"Bearer automation {site.get_automation_secret()}"
    request_url = f"http://localhost/{site.id}/check_mk/api/1.0{request_path}"
    LOGGER.debug("> GET %s", request_url)
    response = session.get(request_url, timeout=5)
    assert response.status_code != 404, f'Invalid API path "{request_path}"!'
    assert response.status_code != 401, f'Invalid authorization for site "{site.id}"!'

    return response


def get_check_results(site: Site, host_name: str) -> dict[str, typing.Any]:
    """Return the current check results from the API."""
    try:
        response = api_get(
            site,
            f"/objects/host/{host_name}/collections/services"
            f"?columns={'&columns='.join(constants.API_SERVICES_COLS)}",
        )
        return {check["id"]: check for check in response.json().get("value", {})}
    except json.decoder.JSONDecodeError as exc:
        raise ValueError(
            "Could not get valid check data! Make sure the site is running "
            "and the provided secret is correct!"
        ) from exc


def compare_check_output(site: Site, output_dir: Path) -> bool:
    """Get the processed check output and compare it to the existing dumps."""
    host_names = [
        host.get("id")
        for host in api_get(site, "/domain-types/host_config/collections/all")
        .json()
        .get("value", [])
        if host.get("id") not in (None, "", site.id)
    ]
    passed = True if constants.UPDATE_MODE else None
    for host_name in host_names:
        if len(constants.HOST_NAMES) > 0 and host_name not in constants.HOST_NAMES:
            continue
        LOGGER.info('> Processing agent host "%s"...', host_name)
        check_results = get_check_results(site, host_name)
        for check_id in sorted(check_results):
            check_result = check_results[check_id]

            check_host_name = check_id.split(":", 1)[0]
            check_display_name = check_result.get(
                "display_name", check_id.split(":", 1)[-1]
            ).replace(f"_{site.id}_", "_SITE_")
            check_safe_name = (
                check_display_name.replace("$", "_").replace(" ", "_").replace("/", "#")
            )
            # equals check_id
            # check_full_name = f"{check_host_name}.{check_display_name}"
            check_file_name = f"{check_host_name}.{check_safe_name}"

            if len(constants.CHECK_NAMES) > 0 and check_file_name not in constants.CHECK_NAMES:
                continue
            json_canon_file_path = f"{constants.EXPECTED_OUTPUT_DIR}/{check_file_name}.json"
            json_result_file_path = str(output_dir / f"{check_file_name}.json")
            result_data = check_result.get("extensions", {})

            if constants.UPDATE_MODE:
                with open(json_canon_file_path, "w", encoding="utf-8") as json_file:
                    json_file.write(f"{json.dumps(result_data, indent=4)}\n")
                continue

            with open(json_result_file_path, "w", encoding="utf-8") as json_file:
                json_file.write(f"{json.dumps(result_data, indent=4)}\n")
            with open(json_canon_file_path, "r", encoding="utf-8") as json_file:
                canon_data = json.load(json_file)

            apply_regexps(check_file_name, canon_data, result_data)

            if result_data and canon_data == result_data:
                if passed is None:
                    passed = True
                continue

            if len(result_data) == 0:
                LOGGER.warning("%s: No data returned!", check_file_name)
            elif canon_data != result_data:
                if len(canon_data) != len(result_data):
                    LOGGER.warning("%s: Data length mismatch!", check_file_name)
                else:
                    LOGGER.warning("%s: Data mismatch!", check_file_name)
            LOGGER.info(run_cmd(["diff", json_canon_file_path, json_result_file_path]).stdout)
            passed = False

    return passed is True
