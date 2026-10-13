#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared library: component ownership from the repository's ``OWNERS`` files.

See tests/qa_metrics/README.md for a tree-level overview.
"""

from ._ownership import (
    ComponentOwnership,
    load_ownership,
    OwnershipUnavailableError,
    UnknownComponentError,
)

__all__ = [
    "ComponentOwnership",
    "OwnershipUnavailableError",
    "UnknownComponentError",
    "load_ownership",
]
