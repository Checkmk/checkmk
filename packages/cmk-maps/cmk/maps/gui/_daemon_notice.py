#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tell the local Maps daemon that a map was deleted or its visibility changed.

The daemon caches who may see a map and keeps its streams open. Told directly
over its socket, it ends them at once instead of after its caches expire. The
notice is signed like a map config, in a context of its own.
"""

import time
from typing import Protocol

from cmk.gui.log import logger
from cmk.maps.shared.map_signature import MAP_WITHDRAWN_CONTEXT, sign_config
from cmk.utils import paths, unixsocket_http
from cmk.utils.local_secrets import SiteInternalSecret

_TIMEOUT = 1.0


class TellDaemon(Protocol):
    def __call__(self, owner: str, name: str, *, deleted: bool) -> None: ...


def withdrawal_notice(owner: str, name: str, *, deleted: bool, now: float) -> dict[str, str]:
    """The body of the daemon's ``withdrawn`` route."""
    return {
        "owner": owner,
        **sign_config(
            {"name": name, "at": now, "deleted": deleted},
            SiteInternalSecret().secret.hmac,
            owner=owner,
            context=MAP_WITHDRAWN_CONTEXT,
        ),
    }


def tell_withdrawn(owner: str, name: str, *, deleted: bool) -> None:
    notice = withdrawal_notice(owner, name, deleted=deleted, now=time.time())
    try:
        unixsocket_http.make_session(paths.tmp_run_dir / "maps.sock", "http://localhost/").post(
            f"http://localhost/api/v1/maps/{name}/withdrawn", json=notice, timeout=_TIMEOUT
        )
    # A stopped daemon has nothing to forget; a running one ends the streams later.
    except OSError as exc:
        logger.debug(
            "Maps daemon not told about map %(name)s: %(error)s", {"name": name, "error": exc}
        )
