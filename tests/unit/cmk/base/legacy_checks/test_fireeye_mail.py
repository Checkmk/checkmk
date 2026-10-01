#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.legacy_checks.fireeye_mail import check_fireeye_mail_received


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="Crash report b0d7751e-242d-11f0-b619-005056b5fc62: ValueError in check_fireeye_mail_received",
)
def test_check_fireeye_mail_received_without_time_window() -> None:
    # The appliance reports an unset statistics window together with zero mails.
    info = [["0"] * 13 + ["00/00/00 00:00:00", "00/00/00 00:00:00", "0"]]

    assert list(check_fireeye_mail_received(None, {}, info)) == [
        (0, "Mails received between 00/00/00 00:00:00 and 00/00/00 00:00:00: 0"),
        (
            3,
            "Cannot compute rate: got time window '00/00/00 00:00:00' to"
            " '00/00/00 00:00:00' (expected MM/DD/YY HH:MM:SS)",
        ),
    ]
