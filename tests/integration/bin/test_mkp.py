#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.site import Site


def test_mkp_help(site: Site) -> None:
    assert "usage: mkp [-h] [--debug]" in site.check_output(["mkp", "--help"])


def test_mkp_find(site: Site) -> None:
    assert "File" in site.check_output(["mkp", "find"])


def test_mkp_show_all(site: Site) -> None:
    assert "Local extension packages" in site.check_output(["mkp", "show-all"])


def test_mkp_list(site: Site) -> None:
    assert "Title" in site.check_output(["mkp", "list"])


def test_mkp_update_active(site: Site) -> None:
    site.check_output(["mkp", "update-active"])


def test_mkp_non_existing(site: Site) -> None:
    with pytest.raises(Exception):
        site.check_output(["mkp", "nubbel"])
