#  #!/usr/bin/env python3
#  Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.licensing.cre_handler import CRELicensingHandler
from cmk.utils.licensing.registry import LicenseState, UserEffect


def test_license_status() -> None:
    handler = CRELicensingHandler()
    assert handler.state is LicenseState.LICENSED
    assert handler.message == ""


def test_user_effect() -> None:
    handler = CRELicensingHandler()
    assert handler.effect() == UserEffect(header=None, email=None, block=None)
