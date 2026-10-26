#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.utils import man_pages


def _broken_man_page(tmp_path: Path) -> Path:
    path = tmp_path / "broken"
    path.write_text("agents: linux\ncatalog: os/misc\n")
    return path


def test_a_broken_man_page_falls_back_to_a_placeholder(tmp_path: Path) -> None:
    man_page = man_pages.parse_man_page("broken", _broken_man_page(tmp_path), debug=False)
    assert man_page.title == "broken: Cannot parse manual page: 'title'"


def test_a_broken_man_page_raises_on_request(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        man_pages.parse_man_page("broken", _broken_man_page(tmp_path), debug=True)
