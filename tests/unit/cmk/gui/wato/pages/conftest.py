#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.watolib.config_domain_name import GlobalSettingsContext
from tests.testlib.unit.gui.config_variable_form_data_test_helper import (
    make_global_settings_context,
)


@pytest.fixture(name="global_settings_context")
def fixture_global_settings_context() -> GlobalSettingsContext:
    return make_global_settings_context(Edition.COMMUNITY)
