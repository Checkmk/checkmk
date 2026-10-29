# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import date

import pytest
from qemu_windows.errors import VmError
from qemu_windows.state import check_expiry

EXPIRES = date(2027, 4, 22)


def test_image_is_refused_from_the_day_before_it_expires() -> None:
    with pytest.raises(VmError, match="expires 2027-04-22: build and pin a new image"):
        check_expiry(EXPIRES, date(2027, 4, 21))


def test_image_passes_until_two_days_before_it_expires() -> None:
    check_expiry(EXPIRES, date(2027, 4, 20))
