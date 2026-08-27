#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.openapi.api_endpoints.global_settings._utils import affected_sites
from cmk.gui.session_context import SuperUserContext
from cmk.gui.watolib.config_domain_name import config_variable_registry


@pytest.mark.usefixtures("request_context")
def test_affected_sites_of_an_event_console_variable() -> None:
    with SuperUserContext():
        assert affected_sites(config_variable_registry["log_level"]) == ["NO_SITE"]


def test_affected_sites_of_an_ordinary_variable() -> None:
    assert affected_sites(config_variable_registry["wato_max_snapshots"]) is None
