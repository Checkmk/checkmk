#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import pytest_helpers

skip_if_not_containerized = pytest.mark.skipif(
    pytest_helpers.not_containerized.condition,
    reason=pytest_helpers.not_containerized.reason,
)

skip_if_not_cloud_edition = pytest.mark.skipif(
    pytest_helpers.not_cloud_edition.condition,
    reason=pytest_helpers.not_cloud_edition.reason,
)

skip_if_raw_edition = pytest.mark.skipif(
    pytest_helpers.is_raw_edition.condition,
    reason=pytest_helpers.is_raw_edition.reason,
)

skip_if_saas_edition = pytest.mark.skipif(
    pytest_helpers.is_saas_edition.condition,
    reason=pytest_helpers.is_saas_edition.reason,
)
