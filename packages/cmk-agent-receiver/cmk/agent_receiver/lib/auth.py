#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
from pathlib import Path
from typing import NewType

from cmk.agent_receiver.lib.config import get_config

B64SiteInternalSecret = NewType("B64SiteInternalSecret", str)

_read_secrets: dict[Path, tuple[tuple[int, int, int], B64SiteInternalSecret]] = {}


def internal_credentials() -> B64SiteInternalSecret:
    """Used on the event loop: a stat per call, a read per change.

    omd regenerates the secret on every start, even of a single daemon, so it must not be
    kept forever. It is rewritten in place with the same length; the mtime tells them apart.
    """
    path = get_config().internal_secret_path
    stat = path.stat()
    key = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
    if (cached := _read_secrets.get(path)) is None or cached[0] != key:
        secret = B64SiteInternalSecret(base64.b64encode(path.read_bytes()).decode("ascii"))
        _read_secrets[path] = cached = (key, secret)
    return cached[1]
