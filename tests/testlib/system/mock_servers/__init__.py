#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Standalone, stdlib-only servers copied into mock containers and run there.

Nothing in here may import from ``cmk`` or ``tests``: the scripts run inside a
plain ``python:3-slim`` container, with only the standard library available.
"""
