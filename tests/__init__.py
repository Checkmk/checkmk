#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Top-level marker for the ``tests`` package.

Kept as a regular package so this directory wins against the unrelated
``tests/`` packages bundled inside individual cmk packages (e.g.
``non-free/packages/cmk-bakery/tests/``) which would otherwise be picked
up first by namespace-package resolution.

Sub-packages (``tests.testlib``, ``tests.testlib.unit``, ...) are PEP 420
namespace packages so contributions from ``non-free/tests/...`` merge
transparently into the same import path.

The ``__path__`` extension below adds ``<repo>/non-free/tests`` so that
``tests.__path__`` covers both source roots; the merge then propagates to
all sub-packages via namespace-package resolution.
"""

import os as _os

_nonfree_tests = _os.path.normpath(
    _os.path.join(_os.path.dirname(__file__), _os.pardir, "non-free", "tests")
)
if _os.path.isdir(_nonfree_tests) and _nonfree_tests not in __path__:
    __path__.append(_nonfree_tests)
