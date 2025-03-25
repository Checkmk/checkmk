#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import pytest
from _pytest.capture import CaptureFixture


def test_import_module(capfd: CaptureFixture) -> None:
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        if sys.version_info[0] == 2:
            import agents.plugins.plesk_domains_2
        else:
            import agents.plugins.plesk_domains  # noqa: F401
    out, _ = capfd.readouterr()
    # PY2 vs PY3: No module named 'MySQLdb' vs No module named MySQLdb
    out = out.replace("'", "")
    assert (
        out
        == "<<<plesk_domains>>>\nNo module named MySQLdb. Please install missing module via pip install <module>."
    )
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 0
