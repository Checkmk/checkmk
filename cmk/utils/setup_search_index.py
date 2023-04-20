#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import TypedDict

from cmk.utils.paths import tmp_dir
from cmk.utils.store import locked

_PATH_UPDATE_REQUESTS = tmp_dir / "search_index_updates.json"


# no pydantic on purpose here to keep things as lean as possible
class UpdateRequests(TypedDict):
    rebuild: bool
    change_actions: list[str]


def request_index_rebuild() -> None:
    with locked(_PATH_UPDATE_REQUESTS):
        _PATH_UPDATE_REQUESTS.write_text(
            json.dumps(
                {
                    "change_actions": _read_update_requests()["change_actions"],
                    "rebuild": True,
                }
            )
        )


def request_index_update(change_action_name: str) -> None:
    with locked(_PATH_UPDATE_REQUESTS):
        current_requests = _read_update_requests()
        _PATH_UPDATE_REQUESTS.write_text(
            json.dumps(
                {
                    "change_actions": list(
                        {
                            *current_requests["change_actions"],
                            change_action_name,
                        }
                    ),
                    "rebuild": current_requests["rebuild"],
                }
            )
        )


def updates_requested() -> bool:
    return _PATH_UPDATE_REQUESTS.exists()


def read_and_remove_update_requests() -> UpdateRequests:
    with locked(_PATH_UPDATE_REQUESTS):
        requests = _read_update_requests()
        _PATH_UPDATE_REQUESTS.unlink(missing_ok=True)
    return requests


def _read_update_requests() -> UpdateRequests:
    if not _PATH_UPDATE_REQUESTS.exists():
        return _noop_update_requests()
    # locking the file touches it, so we must handle this case as well
    if not (raw := _PATH_UPDATE_REQUESTS.read_text()):
        return _noop_update_requests()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # if the file was somehow corrupted, we start from scratch
        return _noop_update_requests()


def _noop_update_requests() -> UpdateRequests:
    return {"rebuild": False, "change_actions": []}
