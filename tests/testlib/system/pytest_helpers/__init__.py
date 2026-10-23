#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pytest plugins for the suites that drive a Checkmk site, and their helpers.

Registered with `registration.register` like the plugins in
tests.testlib.pytest_helpers, but everything here knows about the site under
test and so lives with the other site-level helpers.
"""
