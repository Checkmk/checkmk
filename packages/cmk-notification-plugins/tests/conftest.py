#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True, scope="session")  # ruff: ignore[pytest-fixture-autouse]
def fixture_omd_site() -> Generator[None]:
    os.environ["OMD_SITE"] = "NO_SITE"
    yield
