#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from logging import getLogger
from typing import TypedDict

from cmk.ccc.store import locked
from cmk.utils.paths import tmp_dir

_PATH_UPDATE_REQUESTS = tmp_dir / "search_index_updates.json"


def request_rebuild() -> None:
    with locked(_PATH_UPDATE_REQUESTS):
        current_requests = _read_update_requests()
        current_requests["rebuild"] = True
        _PATH_UPDATE_REQUESTS.write_text(json.dumps(current_requests))


def main() -> None:
    """Entry point for the ``init-redis`` script: request a Setup search index rebuild."""
    logger = getLogger("init-redis")
    try:
        request_rebuild()
    except Exception:
        logger.exception("Failed to request building of Setup search index")


def request_update(change_action_name: str) -> None:
    with locked(_PATH_UPDATE_REQUESTS):
        current_requests = _read_update_requests()
        current_requests["change_actions"].append(change_action_name)
        _PATH_UPDATE_REQUESTS.write_text(json.dumps(current_requests))


# no pydantic on purpose here to keep things as lean as possible
class _UpdateRequests(TypedDict):
    rebuild: bool
    change_actions: list[str]


def _updates_requested() -> bool:
    return _PATH_UPDATE_REQUESTS.exists()


def _read_and_remove_update_requests() -> _UpdateRequests:
    with locked(_PATH_UPDATE_REQUESTS):
        requests = _read_update_requests()
        _PATH_UPDATE_REQUESTS.unlink(missing_ok=True)
    return requests


def _read_update_requests() -> _UpdateRequests:
    try:
        data = json.loads(_PATH_UPDATE_REQUESTS.read_text())
        return _UpdateRequests(
            rebuild=bool(data["rebuild"]),
            change_actions=[str(action) for action in data["change_actions"]],
        )
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        # missing (unlikely, b/c it's locked), empty, or somehow corrupted: start from scratch
        return _UpdateRequests(rebuild=False, change_actions=[])
