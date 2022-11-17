#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.composition.utils import should_skip_because_uncontainerized


@pytest.fixture(scope="module", autouse=True)
def _skip_if_uncontainerized() -> None:
    if should_skip_because_uncontainerized():
        pytest.skip(
            "Tests will install actual agents, which will mess up your local environment (running uncontainerized)"
        )
