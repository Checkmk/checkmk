#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging

from tests.testlib.site import Site

LOGGER = logging.getLogger(__name__)


def test_cmk_migrate_http(site: Site) -> None:
    p = site.run(["cmk-migrate-http", "migrate", "--dry-run"])
    LOGGER.info("STDOUT: %s", p.stdout)
    LOGGER.info("STDERR: %s", p.stderr)
    p.check_returncode()
