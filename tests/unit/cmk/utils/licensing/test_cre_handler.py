#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.licensing.cre_handler import CRELicensingHandler
from cmk.utils.licensing.handler import LicenseState, UserEffect


def test_cre_licensing_handler() -> None:
    cre_handler = CRELicensingHandler()
    assert cre_handler.state is LicenseState.LICENSED
    assert cre_handler.message == ""
    assert cre_handler.effect_core(1, 2) == UserEffect(header=None, email=None, block=None)
    assert cre_handler.effect() == UserEffect(header=None, email=None, block=None)
