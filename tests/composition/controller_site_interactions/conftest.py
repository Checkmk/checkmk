#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.version import version_from_env

from tests.composition.utils import should_skip_because_uncontainerized


@pytest.fixture(scope="module", autouse=True)
def _skip_if_uncontainerized() -> None:
    if should_skip_because_uncontainerized():
        pytest.skip(
            "Tests will install actual agents, which will mess up your local environment (running uncontainerized)"
        )


@pytest.fixture(name="skip_if_not_cloud_edition")
def _skip_if_not_cloud_edition() -> None:
    if not version_from_env().is_cloud_edition():
        pytest.skip("Skipping since we are not testing with a cloud edition")
