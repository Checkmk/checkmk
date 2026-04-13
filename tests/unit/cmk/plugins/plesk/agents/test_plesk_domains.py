#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="no-untyped-call"

import pytest
from _pytest.capture import CaptureFixture  # python 3.4 ...

from cmk.plugins.plesk.agents.plesk_domains import main


def test_import_module(capfd: CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exc:
        main()
    out, _ = capfd.readouterr()
    assert (
        out
        == "<<<plesk_domains>>>\nNo module named 'MySQLdb'. Please install missing module via `pip install mysqlclient`.\n"
    )
    assert exc.value.code == 0
