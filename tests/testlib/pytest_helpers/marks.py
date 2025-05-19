#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides pytest markers for conditionally skipping tests."""

import pytest

from tests.testlib import pytest_helpers

skip_if_not_containerized = pytest.mark.skipif(
    pytest_helpers.not_containerized.condition,
    reason=pytest_helpers.not_containerized.reason,
)
