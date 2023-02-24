#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.version import Edition

from . import conftest

logger = logging.getLogger(__name__)


@pytest.mark.type("update")
def test_update(test_site):
    # TODO: check source installation
    # TODO: set config
    # TODO: get baseline monitoring data

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    conftest.update_site(target_version.version)

    # TODO: check target installation
    # TODO: check config
    # TODO: compare baseline monitoring data
