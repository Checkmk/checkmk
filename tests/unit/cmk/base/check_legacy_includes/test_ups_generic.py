#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.api.agent_based.register.section_plugins_legacy.convert_scan_functions import (
    create_detect_spec,
)
from cmk.base.check_legacy_includes.ups_generic import ups_generic_scan_function
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_GENERIC


def test_scan_functions_stay_in_sync() -> None:
    # we have two different implementation, but we want to make sure they stay
    # in sync. if you change one, you also have to change the other.
    # somewhen ups_generic_scan_function will be removed, then you may also
    # remove this test.
    assert create_detect_spec("", ups_generic_scan_function, []) == DETECT_UPS_GENERIC
