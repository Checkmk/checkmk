#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The backend engine of the support diagnostics domain

Everything the backend (base and GUI) needs beyond the plug-in facing API in
:mod:`cmk.diagnostics.internal`: the selection wire format, the selection
resolution and plug-in loading.

Note: ``cmk.diagnostics`` is a PEP 420 namespace package -- never add a
``cmk/diagnostics/__init__.py``. The ``internal`` portion is contributed by
the cmk-plugin-apis distribution.
"""

from ._loader import load_diagnostics_plugins as load_diagnostics_plugins
from ._selection import resolve_selection as resolve_selection
from ._unsorted import topic_id as topic_id
from ._wire import DumpSelection as DumpSelection
