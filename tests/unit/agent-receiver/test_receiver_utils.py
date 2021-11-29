#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from unittest import mock

from agent_receiver.utils import get_hostname_from_link  # type: ignore[import]


def test_get_hostname_from_link_no_hostname(tmp_path: Path) -> None:
    with mock.patch("agent_receiver.utils.AGENT_OUTPUT_DIR", tmp_path):
        assert get_hostname_from_link("1234") is None


def test_get_hostname_from_link_success(tmp_path: Path) -> None:
    source = tmp_path / "1234"
    target_dir = tmp_path / "hostname"
    source.symlink_to(target_dir)

    with mock.patch("agent_receiver.utils.AGENT_OUTPUT_DIR", tmp_path):
        hostname = get_hostname_from_link("1234")

    assert hostname == "hostname"
