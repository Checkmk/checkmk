#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters import snapvault as gui
from cmk.gui.plugins.wato.check_parameters.snapvault import _parameter_valuespec_snapvault


def test_new_keys_are_stored_in_the_format_of_the_next_major_version() -> None:
    # The rulesets v1 rule of the next major version reads these keys without migration.
    valuespec = _parameter_valuespec_snapvault()
    value = {
        "lag_time": (86400, 172800),
        "policy_lag_time": [("Asynchronous", (3600, 7200))],
        "transfer_state": dict(gui.DEFAULT_TRANSFER_STATE),
        "unhealthy_state": gui.DEFAULT_UNHEALTHY_STATE,
    }

    valuespec.validate_datatype(value, "")
    valuespec.validate_value(value, "")


def test_transfer_state_rejects_missing_states() -> None:
    valuespec = _parameter_valuespec_snapvault()

    with pytest.raises(MKUserError):
        valuespec.validate_datatype({"transfer_state": {"failed": 2}}, "")
