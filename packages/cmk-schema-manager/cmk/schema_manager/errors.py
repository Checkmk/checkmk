#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations


class SchemaManagerError(Exception):
    """Base class of every error the schema manager raises on its own."""


class InvalidRevisionChainError(SchemaManagerError, ValueError):
    """A `RevisionChain` was constructed from invalid revisions."""
