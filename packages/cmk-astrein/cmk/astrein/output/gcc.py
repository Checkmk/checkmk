#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""GCC-style output, understood by IDEs and Bazel."""

from cmk.astrein.framework import CheckerError


def format_gcc(error: CheckerError) -> str:
    return f"{error.file_path}:{error.line}:{error.column}: error: [{error.checker_id}] {error.message}"
