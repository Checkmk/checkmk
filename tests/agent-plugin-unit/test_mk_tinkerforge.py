#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import hashlib
from io import BytesIO

import pytest

from agents.plugins import mk_tinkerforge


def test_check_digest_accepts_matching_digest() -> None:
    data = b"some test data"
    mk_tinkerforge.check_digest(BytesIO(data), hashlib.sha256(data).hexdigest())


def test_check_digest_rejects_mismatching_digest() -> None:
    with pytest.raises(ValueError):
        mk_tinkerforge.check_digest(BytesIO(b"some test data"), 64 * "0")


class _Identifier:
    connected_uid = "6yLduG"
    position = "a"
    uid = "6Kvbc1"


def test_id_to_string() -> None:
    assert mk_tinkerforge.id_to_string(_Identifier()) == "6yLduG.a.6Kvbc1"
