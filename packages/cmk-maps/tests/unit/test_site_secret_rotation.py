#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The daemon picks up a rotated site-internal secret, against the real secret file."""

import os
from pathlib import Path

import pytest

from cmk.crypto.secrets import Secret
from cmk.maps.backend.core.auth import InvalidSignature, verify_map_config
from cmk.maps.shared.map_signature import sign_config

_CONFIG: dict[str, object] = {"name": "shared"}


def _signed(secret: Secret) -> dict[str, str]:
    return sign_config(_CONFIG, secret.hmac, owner="alice")


def _verify(signed: dict[str, str]) -> dict[str, object]:
    return verify_map_config(signed["config_b64"], signed["sig"], owner="alice")


def test_empty_secret_file_is_left_for_omd_to_write(site_secret_file: Path) -> None:
    # omd has truncated the file and not yet written the new secret.
    with pytest.raises(InvalidSignature):
        _verify(_signed(Secret(os.urandom(32))))

    assert site_secret_file.read_bytes() == b""


def test_rewrite_within_one_mtime_tick_is_picked_up(site_secret_file: Path) -> None:
    # The daemon reads the truncated file, then omd writes the real secret within
    # the same coarse mtime tick.
    truncated = site_secret_file.stat()
    omd_secret = Secret(os.urandom(32))
    signed = _signed(omd_secret)
    with pytest.raises(InvalidSignature):
        _verify(signed)

    site_secret_file.write_bytes(omd_secret.reveal())
    os.utime(site_secret_file, ns=(truncated.st_atime_ns, truncated.st_mtime_ns))

    assert _verify(signed) == _CONFIG
