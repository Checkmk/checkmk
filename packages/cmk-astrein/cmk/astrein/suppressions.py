#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import re
import tokenize
from collections.abc import Sequence
from dataclasses import dataclass

_SUPPRESSION_PATTERN = re.compile(r"astrein: disable=([\w-]+)")


@dataclass(frozen=True)
class Suppression:
    """An inline ``# astrein: disable=<checker-id>`` comment."""

    checker_id: str
    line: int
    column: int
    covers_next_line: bool

    def covers(self, line: int) -> bool:
        return line == self.line or (self.covers_next_line and line == self.line + 1)


def parse_suppressions(source_code: str) -> Sequence[Suppression]:
    """Find all suppressions in actual comments, ignoring look-alikes in strings."""
    return [
        Suppression(
            checker_id=match.group(1),
            line=token.start[0],
            column=token.start[1] + match.start(),
            covers_next_line=not token.line[: token.start[1]].strip(),
        )
        for token in tokenize.generate_tokens(io.StringIO(source_code).readline)
        if token.type == tokenize.COMMENT
        for match in _SUPPRESSION_PATTERN.finditer(token.string)
    ]
