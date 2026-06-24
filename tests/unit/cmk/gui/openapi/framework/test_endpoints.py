#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.ccc.version import Edition
from tests.testlib.openapi_endpoint_validation import assert_registered_endpoints_valid


@pytest.mark.usefixtures("load_plugins")
def test_verify_registered_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    """All versioned endpoints registered for the community edition are framework-valid.

    The non-free editions are validated by the equivalent per-edition tests under
    ``tests/unit/cmk/gui/nonfree/<edition>/openapi/``; this lane is edition-pinned
    to community.
    """
    assert_registered_endpoints_valid(Edition.COMMUNITY, monkeypatch)
