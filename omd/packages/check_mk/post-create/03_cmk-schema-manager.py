#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

from cmk.schema_manager.backend.sqlite import ensure_sqlite_created

if __name__ == "__main__":
    ensure_sqlite_created(logging.getLogger("cmk.schema_manager"))
