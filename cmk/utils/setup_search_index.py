#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import TypedDict

from cmk.ccc.store import locked
from cmk.utils.paths import tmp_dir

_PATH_UPDATE_REQUESTS = tmp_dir / "search_index_updates.json"


# no pydantic on purpose here to keep things as lean as possible
class UpdateRequests(TypedDict):
    rebuild: bool
    change_actions: list[str]


def request_index_rebuild() -> None:
    with locked(_PATH_UPDATE_REQUESTS):
        current_requests = _read_update_requests()
        current_requests["rebuild"] = True
        _PATH_UPDATE_REQUESTS.write_text(json.dumps(current_requests))


def request_index_update(change_action_name: str) -> None:
    with locked(_PATH_UPDATE_REQUESTS):
        current_requests = _read_update_requests()
        current_requests["change_actions"].append(change_action_name)
        _PATH_UPDATE_REQUESTS.write_text(json.dumps(current_requests))


def updates_requested() -> bool:
    return _PATH_UPDATE_REQUESTS.exists()


def read_and_remove_update_requests() -> UpdateRequests:
    with locked(_PATH_UPDATE_REQUESTS):
        requests = _read_update_requests()
        _PATH_UPDATE_REQUESTS.unlink(missing_ok=True)
    return requests


def _read_update_requests() -> UpdateRequests:
    try:
        return json.loads(_PATH_UPDATE_REQUESTS.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        # missing (unlikely, b/c it's locked), empty, or somehow corrupted: start from scratch
        return {"rebuild": False, "change_actions": []}
