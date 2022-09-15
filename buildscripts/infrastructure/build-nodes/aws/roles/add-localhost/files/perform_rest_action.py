#!/usr/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import time
from typing import Callable, Mapping

import requests


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-entrypoint",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--automation-secret",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--action",
        action="store",
        required=True,
        choices=action_to_function.keys(),
    )
    return parser.parse_args()


def add_localhost(entrypoint: str, my_session: requests.Session) -> None:
    resp = my_session.post(
        f"{entrypoint}/domain-types/host_config/collections/all",
        json={
            "host_name": "localhost",
            "folder": "/",
            "attributes": {
                "ipaddress": "127.0.0.1",
            },
        },
    )
    assert resp.status_code == 200, f"{resp.status_code=}, {resp.text=}"


def remove_localhost(entrypoint: str, my_session: requests.Session) -> None:
    resp = my_session.delete(
        f"{entrypoint}/objects/host_config/localhost",
    )
    assert resp.status_code == 204, f"{resp.status_code=}, {resp.text=}"


def discover_services(entrypoint: str, my_session: requests.Session) -> None:
    resp = my_session.post(
        f"{entrypoint}/domain-types/service_discovery_run/actions/start/invoke",
        json={"host_name": "localhost", "mode": "fix_all"},
        allow_redirects=False,
    )
    while resp.status_code == 302:
        resp = my_session.get(
            f"{entrypoint}/objects/service_discovery_run/localhost/actions/wait-for-completion/invoke",
            allow_redirects=False,
        )
        time.sleep(1)
    assert resp.status_code == 200, f"{resp.status_code=}, {resp.text=}"


def activate_changes(entrypoint: str, my_session: requests.Session) -> None:
    resp = my_session.post(
        f"{entrypoint}/domain-types/activation_run/actions/activate-changes/invoke",
        json={"redirect": False},
        allow_redirects=False,
    )
    activation_id = resp.json()["id"]
    while resp.status_code == 302:
        resp = my_session.get(
            f"{entrypoint}/objects/activation_run/{activation_id}/actions/wait-for-completion/invoke",
        )
        time.sleep(1)
    assert resp.status_code == 200, f"{resp.status_code=}, {resp.text=}"


action_to_function: Mapping[str, Callable[[str, requests.Session], None]] = {
    "add_localhost": add_localhost,
    "remove_localhost": remove_localhost,
    "activate_changes": activate_changes,
    "discover_services": discover_services,
}
if __name__ == "__main__":

    args = parse_args()

    session = requests.session()
    session.headers["Authorization"] = f"Bearer automation {args.automation_secret}"
    session.headers["Accept"] = "application/json"
    session.headers["Content-Type"] = "application/json"

    action_to_function[args.action](args.api_entrypoint, session)
