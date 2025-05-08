#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.openapi.framework.model.validators import HostAddressValidator


class TestHostAddressValidator:
    def test_allow_empty(self) -> None:
        validator = HostAddressValidator(allow_empty=True)
        assert validator("") == ""

    def test_forbid_empty(self) -> None:
        validator = HostAddressValidator(allow_empty=False)
        with pytest.raises(ValueError, match="Empty host address is not allowed"):
            validator("")

    @pytest.mark.parametrize("value", ["192.168.0.1"])
    def test_allow_ipv4(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv4=True)
        assert validator(value) == value

    @pytest.mark.parametrize("value", ["192.168.0.1"])
    def test_forbid_ipv4(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv4=False)
        with pytest.raises(ValueError, match="IPv4 address.* not allowed"):
            validator(value)

    @pytest.mark.parametrize("value", ["2001:db8::1"])
    def test_allow_ipv6(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv6=True)
        assert validator(value) == value

    @pytest.mark.parametrize("value", ["2001:db8::1"])
    def test_forbid_ipv6(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv6=False)
        with pytest.raises(ValueError, match="IPv6 address.* not allowed"):
            validator(value)

    @pytest.mark.parametrize("value", ["example.com"])
    def test_allow_hostname(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv4=False, allow_ipv6=False, allow_empty=False)
        assert validator(value) == value
