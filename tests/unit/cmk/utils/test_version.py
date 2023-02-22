#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.utils.version import Version


class TestVersion:
    def test_stable(self) -> None:
        assert Version("1.2.3")

    def test_innovation(self) -> None:
        assert Version("1.2.4i8")

    def test_beta(self) -> None:
        assert Version("1.2.4b1")

    def test_patch(self) -> None:
        assert Version("1.2.4p3")

    def test_stable_daily(self) -> None:
        assert Version("1.2.3-2023.12.24")

    def test_master_daily(self) -> None:
        assert Version("2023.12.24")

    def test_invalid_vtype(self) -> None:
        with pytest.raises(ValueError):
            _version = Version("1.2.3g5")

    def test_invalid_combo(self) -> None:
        # currently invalid.
        with pytest.raises(ValueError):
            _version = Version("1.2.3b5-2023.01.01")

    def test_version_base_master(self) -> None:
        assert Version("1984.04.01").version_base == ""

    def test_version_base_stable(self) -> None:
        assert Version("1.2.3").version_base == "1.2.3"

    def test_version_base_release(self) -> None:
        assert Version("4.5.6p8").version_base == "4.5.6"

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (Version("1.2.3"), "Version('1.2.3')"),
            (Version("2024.03.14"), "Version('2024.03.14')"),
            (Version("3.4.5p8"), "Version('3.4.5p8')"),
            (Version("1.2.3-2024.09.09"), "Version('1.2.3-2024.09.09')"),
        ],
    )
    def test_repr(self, vers: Version, expected: str) -> None:
        assert repr(vers) == expected

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (Version("1.2.3"), "1.2.3"),
            (Version("2024.03.14"), "2024.03.14"),
            (Version("3.4.5p8"), "3.4.5p8"),
            (Version("1.2.3-2024.09.09"), "1.2.3-2024.09.09"),
        ],
    )
    def test_str(self, vers: Version, expected: str) -> None:
        assert str(vers) == expected

    @pytest.mark.parametrize(
        "smaller, bigger",
        [
            (Version("1.2.3"), Version("1.2.4")),
            (Version("2024.03.12"), Version("2024.03.14")),
            (Version("3.4.5p8"), Version("3.5.5p4")),
            (Version("1.2.3-2024.09.09"), Version("1.2.4-1970.01.01")),
        ],
    )
    def test_lt(self, smaller: Version, bigger: Version) -> None:
        assert smaller < bigger

    @pytest.mark.parametrize(
        "one, other, equal",
        [
            (Version("1.2.3"), Version("1.2.3"), True),
            (Version("1.2.3"), Version("1.3.3"), False),
            (Version("2024.03.14"), Version("2024.03.14"), True),
            (Version("2024.03.13"), Version("2024.03.14"), False),
            (Version("3.4.5p8"), Version("3.4.5p8"), True),
            (Version("3.4.5p8"), Version("3.4.5p7"), False),
            (Version("1.2.3-2024.09.09"), Version("1.2.3-2024.09.09"), True),
            (Version("1.2.3-2024.09.09"), Version("1.2.3-2024.09.19"), False),
            (Version("2024.03.13"), Version("3.4.5p8"), False),
        ],
    )
    def test_eq(self, one: Version, other: Version, equal: bool) -> None:
        assert (one == other) is equal

    @pytest.mark.parametrize(
        "version_string, expected",
        [
            ("1.5.0-2019.10.10", 1050090000),
            ("1.6.0-2019.10.10", 1060090000),
            ("1.5.0-2019.10.24", 1050090000),
            ("1.2.4p1", 1020450001),
            ("1.2.4", 1020450000),
            ("1.2.4b1", 1020420100),
            ("1.2.3p1", 1020350001),
            ("1.2.3i1", 1020310100),
            ("1.2.4p10", 1020450010),
            ("1.5.0-2019.10.10", 1050090000),
            ("1.5.0p22", 1050050022),
            ("2022.06.23-sandbox-az-sles-15sp3", 2022062390000),
        ],
    )
    def test_parse_to_int(self, version_string: str, expected: int) -> None:
        assert Version(version_string).parse_to_int() == expected
        # FIXME: test consistentcy
        # assert parse_check_mk_version(version_string) == expected
