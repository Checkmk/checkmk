# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk_dev_site.utils.log import colorize


def test_colorize() -> None:
    assert colorize("test", "blue") == "\033[34mtest\033[0m"
    assert colorize("test", "red") == "\033[31mtest\033[0m"
    assert colorize("test", "unknown") == "test"
