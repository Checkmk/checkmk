#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resolve the application version.

The daemon ships in-tree and is versioned with Checkmk itself (the package
already depends on //packages/cmk-ccc:version), so the single source of truth is
``cmk.ccc.version.__version__`` — no separate VERSION file to keep in sync.
"""

from cmk.ccc.version import __version__

APP_VERSION = __version__
