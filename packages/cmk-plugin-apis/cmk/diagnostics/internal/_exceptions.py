#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Exceptions a plugin handler may raise to report on its collection

They are caught per plugin by the dump engine and end up in the dump's
console log at the corresponding level. Files the handler yielded before
raising remain part of the dump.
"""


# TODO: get rid of this entirely. The plugin can just log.


class CollectInfo(Exception):
    """Raise in a handler to report there is nothing to do"""


class CollectWarning(Exception):
    """Raise in a handler to report a non-fatal problem"""


class CollectError(Exception):
    """Raise in a handler to report that collection failed"""
