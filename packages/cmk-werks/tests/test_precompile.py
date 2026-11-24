#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from pathlib import Path

from cmk.ccc.version import __version__
from cmk.werks.utils import load_precompiled_werks_file
from cmk.werks.utils.__main__ import main_precompile


def test_precompile_sets_the_current_version(tmp_path: Path) -> None:
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    (werk_dir / "1234.md").write_text(
        """[//]: # (werk v2)
# Some title

key        | value
---------- | ---
date       | 2026-07-23T08:04:44.815279+00:00
class      | fix
edition    | cre
component  | core
level      | 1
compatible | yes

Some description.
"""
    )
    destination = tmp_path / "precompiled.json"

    main_precompile(
        argparse.Namespace(werk_dir=werk_dir, destination=destination, filter_by_edition=None)
    )

    assert load_precompiled_werks_file(destination)[1234].version == __version__
