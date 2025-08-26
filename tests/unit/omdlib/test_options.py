#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.options import main_help


def test_main_help(capsys: pytest.CaptureFixture[str]) -> None:
    main_help()
    stdout = capsys.readouterr()[0]
    assert "omd COMMAND -h" in stdout
