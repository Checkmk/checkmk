#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from tests.testlib.openapi_spec_parity import assert_slim_registration_matches_app


@pytest.mark.usefixtures("load_plugins")
def test_slim_registration_matches_app_for_community(monkeypatch: pytest.MonkeyPatch) -> None:
    assert_slim_registration_matches_app(Edition.COMMUNITY, monkeypatch)
