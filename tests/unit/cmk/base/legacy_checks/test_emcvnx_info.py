#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.legacy_checks.emcvnx_info import check_emcvnx_info, parse_emcvnx_info


@pytest.mark.xfail(strict=True, raises=IndexError, reason="Crash group 4478: IndexError")
def test_check_emcvnx_info_cli_error_only() -> None:
    # Crash group 4478: naviseccli printed only an error message
    parsed = parse_emcvnx_info([["Unknown exception while executing cli command"]])
    assert list(check_emcvnx_info(None, None, parsed)) == [
        (
            2,
            "Error(s) while parsing the output. This may effect the discovery of other "
            "emcvnx services. Please check your naviseccli configuration. Errors are: "
            "Unknown exception while executing cli command",
        ),
    ]
