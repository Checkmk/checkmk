#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.werks import load_raw_files_old


def test_website_essentials_workaround():
    werks = load_raw_files_old(Path(".werks"))

    for w in werks:
        werk_dict = w.to_json_dict()
        assert werk_dict.get("__version__") is None
