#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Community edition run of the config variable disk-data round-trip tests,
see tests.testlib.unit.gui.config_variable_form_data_test_helper for the
suite. The test job pins EDITION=community (tests/unit/cmk/gui/wato/BUILD);
the config variables of the other editions are covered by the sibling tests
in tests/unit/cmk/gui/nonfree/*/wato/."""

from tests.testlib.unit.gui.config_variable_form_data_test_helper import (
    ConfigVariableSuite,
    generate_config_variable_tests,
)

pytest_generate_tests = generate_config_variable_tests


class TestConfigVariableFormData(ConfigVariableSuite):
    pass
