#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_redis_client(site: Site) -> None:
    assert site.python_helper("helper_test_redis_client.py").check_output().rstrip() == "True"
