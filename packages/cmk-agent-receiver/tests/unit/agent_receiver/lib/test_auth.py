#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import os

from cmk.agent_receiver.lib.auth import internal_credentials
from cmk.agent_receiver.lib.config import Config


def test_regenerated_secret_is_used_without_restart(setup_site_context: Config) -> None:
    path = setup_site_context.internal_secret_path
    path.write_bytes(b"old-secret")
    assert internal_credentials() == base64.b64encode(b"old-secret").decode("ascii")

    # Rewritten in place with the same length, as omd does, at a later start.
    stat = path.stat()
    path.write_bytes(b"new-secret")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    assert internal_credentials() == base64.b64encode(b"new-secret").decode("ascii")
