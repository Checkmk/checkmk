#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.misc import gen_id, validate_uuid_str


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Valid canonical lowercase UUIDs — returned unchanged
        ("550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440000"),
        ("00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000"),
        # Uppercase — rejected (not in the form produced by gen_id)
        ("550E8400-E29B-41D4-A716-446655440000", None),
        # Mixed case — rejected
        ("550e8400-E29B-41d4-A716-446655440000", None),
        # Too short
        ("550e8400-e29b-41d4-a716", None),
        # Wrong structure (no hyphens)
        ("550e8400e29b41d4a716446655440000", None),
        # Path traversal attempt
        ("../etc/passwd", None),
        ("../../secret", None),
        # Empty / None
        ("", None),
        (None, None),
        # Only hyphens and hex but not UUID-shaped
        ("----", None),
        ("abcdef", None),
        ("ff", None),
    ],
)
def test_validate_uuid_str(raw: str | None, expected: str | None) -> None:
    assert validate_uuid_str(raw) == expected


def test_validate_uuid_str_accepts_gen_id_output() -> None:
    """IDs produced by gen_id() must always pass validation unchanged."""
    for _ in range(20):
        generated = gen_id()
        assert validate_uuid_str(generated) == generated
