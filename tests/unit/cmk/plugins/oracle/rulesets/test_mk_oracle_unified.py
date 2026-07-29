#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest

from cmk.plugins.oracle.rulesets.mk_oracle_unified import (
    _agent_config_mk_oracle,
    USE_HOST_CLIENT_PATH_RE,
)
from cmk.rulesets.v1.form_specs import Dictionary


def test_options_is_top_level() -> None:
    # `options` is a top-level GUI section; the bakery routes it into `oracle.main.options`
    form = _agent_config_mk_oracle()
    assert "options" in form.elements, "`options` must be a top-level element"
    main_form = form.elements["main"].parameter_form
    assert isinstance(main_form, Dictionary)
    assert "options" not in main_form.elements, "`options` must not be nested under `main`"


@pytest.mark.parametrize(
    "value",
    [
        "/usr/lib/oracle",
        "/usr/lib/oracle/21/client64/lib",
        "$OCI_DIR/lib",
        "${OCI_DIR}/lib",
        "C:/oracle/client",
        "C:\\oracle\\client",
        "D:\\oracle\\product\\19c",
    ],
)
def test_use_host_client_path_regex_accepts_valid(value: str) -> None:
    assert re.match(USE_HOST_CLIENT_PATH_RE, value), f"Expected {value!r} to be accepted"


@pytest.mark.parametrize(
    "value",
    [
        "",  # empty
        "$",  # bare dollar — no variable name
        "relative/path",
        "oracle/lib",
        "1:\\bad_drive",  # invalid Windows drive letter
    ],
)
def test_use_host_client_path_regex_rejects_invalid(value: str) -> None:
    assert not re.match(USE_HOST_CLIENT_PATH_RE, value), f"Expected {value!r} to be rejected"
