#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import tempfile
from pathlib import Path

import lark
import pysmi.parser.lark_parser
import pytest


def pytest_configure(config: pytest.Config) -> None:
    _cache_pysmi_parser_tables(config)


def _cache_pysmi_parser_tables(config: pytest.Config) -> None:
    """Each pysmi parser builds the LALR tables of its lark parser, which takes most of the time of
    the MIB compiler tests. Let lark cache them in a file for the session, so that every parser is
    still a new one, e.g. the reference ones of pysmi."""
    cache_dir = tempfile.TemporaryDirectory()
    config.add_cleanup(cache_dir.cleanup)
    patch = pytest.MonkeyPatch()
    config.add_cleanup(patch.undo)
    patch.setattr(
        pysmi.parser.lark_parser,
        "Lark",
        functools.partial(lark.Lark, cache=str(Path(cache_dir.name) / "smi.lark")),
    )
