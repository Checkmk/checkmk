#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers and pytest-plugins

These can be loaded or registered, respectively, at runtime during a testsuite setup.

Keep this module free of imports. tests/scripts/resolve_shard_durations.py reads
the shard durations from `sharding` in a CI container that has no pytest
installed, and importing any module of this package runs this one first.
"""
