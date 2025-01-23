#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterator

import pytest

from tests.testlib.emails import create_notification_user
from tests.testlib.site import Site


@pytest.fixture(name="notification_user", scope="function")
def notification_user(test_site: Site) -> Iterator[tuple[str, str]]:
    yield from create_notification_user(test_site)
