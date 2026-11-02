#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs.generators.host_address import HostAddressValidator
from cmk.rulesets.v1.form_specs.validators import ValidationError


def test_invalid_address_error_names_all_allowed_kinds_of_addresses() -> None:
    with pytest.raises(ValidationError) as excinfo:
        HostAddressValidator()("not a host!")

    assert excinfo.value.message.localize(lambda text: text) == (
        "Host- or DNS name, IPv4 address, IPv6 address"
    )
