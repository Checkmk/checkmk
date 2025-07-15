#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.licensing.registry import licensing_handler_registry, register_cre_licensing_handler


def test_licensing_handler_registry_cre() -> None:
    register_cre_licensing_handler()
    handler_class = licensing_handler_registry[Edition.CRE]
    assert handler_class.__name__ == "CRELicensingHandler"
    assert issubclass(handler_class, LicensingHandler)
