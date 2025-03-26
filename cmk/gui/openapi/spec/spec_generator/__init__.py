#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Spec/Documentation building code

The `code_examples` module contains a helper which renders Jinja2
templates with source code examples. These are put into the spec
by the decorator. The examples are specific to the Redoc documentation
generator library.
"""

from ._core import main

__all__ = ["main"]
