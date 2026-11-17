#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.man_pages import (
    _man_request,
    _RENDERER_VALUE,
    ManRequest,
)


def test_the_man_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _RENDERER_VALUE: ["nowiki"],
        CLIOptionalArgument(placeholder="CHECKTYPE", parse=str): ["df"],
    }

    assert _man_request(CLIReader(lambda declaration: given.get(declaration, ()))) == ManRequest(
        renderer="nowiki", check_type="df"
    )


def test_an_unknown_renderer_is_rejected() -> None:
    with pytest.raises(ValueError, match="html"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {_RENDERER_VALUE: ["html"]}

        _man_request(CLIReader(lambda declaration: given.get(declaration, ())))
