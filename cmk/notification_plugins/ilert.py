#!/usr/bin/env python3
# iLert Checkmk Native Plugin

# Copyright (c) 2013-2020, iLert GmbH
#       iLert <support@ilert.com>
# License: GNU Public License v2

import sys
from http.client import responses as http_responses
from os import environ
from typing import NoReturn

import requests

from cmk.notification_plugins.utils import post_request, process_by_result_map
from cmk.notification_plugins.utils import retrieve_from_passwordstore as passwords
from cmk.notification_plugins.utils import StateInfo

PLUGIN_VERSION = "1.0"

HEADERS = {
    "Content-type": "application/json",
    "Accept": "application/json",
    "Agent": "checkmk/extension/%s" % PLUGIN_VERSION,
}

RESULT_MAP = {
    (200, 299): StateInfo(0, "json", "incidentKey"),
    (300, 399): StateInfo(2, "str", "Error"),
    (400, 428): StateInfo(2, "str", "Event not accepted by iLert"),
    (429, 429): StateInfo(1, "str", "Too many requests, will try again. Server response"),
    (430, 499): StateInfo(2, "str", "Event not accepted by iLert"),
    (500, 599): StateInfo(1, "str", "Server error"),
}


def _ilert_url() -> str:
    password = passwords(environ["NOTIFY_PARAMETER_ILERT_API_KEY"])
    return f"https://api.ilert.com/api/v1/events/checkmk-ext/{password}"


def _check_return_code(response: requests.Response) -> None:
    # this is a hotfix for 2.2
    # in 2.3, process_by_result_map was changed so that this function will no longer be needed
    try:
        body = response.json()
    except requests.JSONDecodeError:
        return

    if not (code := body.get("code")):
        return

    status_code = response.status_code
    summary = f"{status_code}: {http_responses[status_code]}"
    if status_code == 400 and code == "NONE_OPEN_FOR_KEY":
        sys.stderr.write(f"Event already closed in iLert: {response.text}\n{summary}\n")
        sys.exit(0)


def main() -> NoReturn:
    response = post_request(lambda context: {**context}, url=_ilert_url(), headers=HEADERS)
    _check_return_code(response)
    process_by_result_map(response, RESULT_MAP)
