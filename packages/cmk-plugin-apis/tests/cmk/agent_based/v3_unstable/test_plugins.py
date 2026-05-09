#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator
from typing import Never

import pytest

from cmk.agent_based.v3_unstable import CheckPlugin

INVALID_NAMES = ["", *"\"'^°!²³§$½¬%&/{([])}=?ß\\'`*+~#-.:,;ÜÖÄüöä<>|"]


def _noop(*_a: object) -> Generator[Never]:
    yield from ()


@pytest.mark.parametrize("str_name", INVALID_NAMES)
def test_invalid_check_plugin_name(str_name: str) -> None:
    with pytest.raises(ValueError):
        _ = CheckPlugin(
            name=str_name,
            service_name="foo",
            discovery_function=_noop,
            check_function=_noop,
        )
