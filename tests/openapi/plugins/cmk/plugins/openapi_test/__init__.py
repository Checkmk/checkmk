#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A plug-in family for the REST API tests only.

The REST API behaviour under test does not depend on any particular plug-in, so the tests use
these instead of whatever plug-ins happen to ship. Plug-in discovery loads them like any other
family, as long as this target is in the test's runfiles."""
