#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.gui.pagetypes import _deserialize_public


@pytest.mark.parametrize(
    "public, expected",
    [
        (None, False),
        (True, True),
        (("contact_groups", ["first", "second"]), ("contact_groups", ["first", "second"])),
        (("sites", ["mysite", "mysite_2"]), ("sites", ["mysite", "mysite_2"])),
    ],
)
def test_deserialize_public(
    public: object,
    expected: tuple[Literal["contact_groups", "sites"], Sequence[str]] | bool,
) -> None:
    assert _deserialize_public(public) == expected
