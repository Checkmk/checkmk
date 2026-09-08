#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers and pytest-plugins

These can be loaded or registered, respectively, at runtime during a testsuite setup.

Every module here imports pytest, so nothing that has to run without it may import
from this package. tests/scripts/resolve_shard_durations.py is such a caller; the
planning it needs lives in tests/testlib/system/shard_planning.py.
"""
