#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""cmk.crypto keeps copies of identifier patterns of cmk.ccc.regex: they must not drift apart"""

from cmk.ccc.regex import REGEX_ID, SITE_ID_PATTERN
from cmk.crypto.x509 import CUSTOMER_ID_PATTERN, SITE_NAME_PATTERN


def test_certificates_accept_the_site_names_checkmk_accepts() -> None:
    assert SITE_NAME_PATTERN == SITE_ID_PATTERN


def test_certificates_accept_the_customer_ids_checkmk_accepts() -> None:
    assert CUSTOMER_ID_PATTERN == REGEX_ID
