#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

from tests.testlib.utils import version_spec_from_env


# TODO: Better hand over arguments using pytest mechanisms (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def package_path() -> str:
    path = os.environ.get("PACKAGE_PATH")
    if not path:
        raise Exception(
            "PACKAGE_PATH environment variable pointing to the package to be tested is missing"
        )
    return path


# TODO: Better hand over arguments using pytest mechanisms (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def cmk_version() -> str:
    return version_spec_from_env()
