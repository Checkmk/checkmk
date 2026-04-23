#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Re-export from cmk.web. The implementation has moved there; callers can be
# migrated incrementally.
from cmk.web.utils.escaping import (
    ALLOWED_TAGS as ALLOWED_TAGS,
)
from cmk.web.utils.escaping import (
    escape as escape,
)
from cmk.web.utils.escaping import (
    escape_permissive as escape_permissive,
)
