#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.man_pages import (
    _renderer_request,
    _RENDERER_VALUE,
)


def test_the_renderer_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {_RENDERER_VALUE: ["nowiki"]}

    assert _renderer_request(CLIReader(lambda declaration: given.get(declaration, ()))) == "nowiki"


def test_an_unknown_renderer_is_rejected() -> None:
    with pytest.raises(ValueError, match="html"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {_RENDERER_VALUE: ["html"]}

        _renderer_request(CLIReader(lambda declaration: given.get(declaration, ())))
