#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.version import _VersionCommand


def _ultimate(_omd_root: Path) -> Edition:
    return Edition.ULTIMATE


def test_the_version_names_the_sites_edition(capsys: pytest.CaptureFixture[str]) -> None:
    context = CLIContext(
        omd_root=Path("/omd/sites/mysite"),
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )

    _VersionCommand(edition_of=_ultimate).run(context, None)

    assert capsys.readouterr().out.startswith("This is Checkmk Ultimate version ")
