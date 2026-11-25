# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.crypto import der


def test_der() -> None:
    assert der._DERData.from_bytes(b"abc").bytes == b"abc"  # noqa
    assert der._DERData.from_bytes(b"abc").base64_str == "YWJj"  # noqa
    assert der._DERData.from_base64("YWJj").bytes == b"abc"  # noqa
    assert der._DERData.from_base64(b"YWJj").base64_str == "YWJj"  # noqa
