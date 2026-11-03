#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import get_args

import pytest

from cmk.werks.tool.flavor_registry import FLAVOR_NAMES, get_flavor
from cmk.werks.tool.models import WebsiteWerkV3


@pytest.mark.parametrize("name", FLAVOR_NAMES)
def test_every_flavor_is_published_as_a_product(name: str) -> None:
    assert get_flavor(name).name in get_args(WebsiteWerkV3.model_fields["product"].annotation)


def test_an_unknown_flavor_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown flavor 'unknown'"):
        get_flavor("unknown")
