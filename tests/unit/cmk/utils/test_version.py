#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.version import parse_check_mk_version, Version


class TestVersion:
    def test_stable(self) -> None:
        assert Version.from_str("1.2.3")

    def test_innovation(self) -> None:
        assert Version.from_str("1.2.4i8")

    def test_beta(self) -> None:
        assert Version.from_str("1.2.4b1")

    def test_patch(self) -> None:
        assert Version.from_str("1.2.4p3")

    def test_stable_daily(self) -> None:
        assert Version.from_str("1.2.3-2023.12.24")

    def test_master_daily(self) -> None:
        assert Version.from_str("2023.12.24")

    def test_invalid_vtype(self) -> None:
        with pytest.raises(ValueError):
            _version = Version.from_str("1.2.3g5")

    def test_invalid_combo(self) -> None:
        # currently invalid.
        with pytest.raises(ValueError):
            _version = Version.from_str("1.2.3b5-2023.01.01")

    def test_version_base_master(self) -> None:
        assert Version.from_str("1984.04.01").version_base == ""

    def test_version_base_stable(self) -> None:
        assert Version.from_str("1.2.3").version_base == "1.2.3"

    def test_version_base_release(self) -> None:
        assert Version.from_str("4.5.6p8").version_base == "4.5.6"

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (
                Version.from_str("1.2.3"),
                "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(r_type=RType.na, value=0))",
            ),
            (
                Version.from_str("2024.03.14"),
                "Version(None, _Release(r_type=RType.daily, value=_BuildDate(year=2024, month=3, day=14)))",
            ),
            (
                Version.from_str("3.4.5p8"),
                "Version(_BaseVersion(major=3, minor=4, sub=5), _Release(r_type=RType.p, value=8))",
            ),
            (
                Version.from_str("1.2.3-2024.09.09"),
                "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(r_type=RType.daily, value=_BuildDate(year=2024, month=9, day=9)))",
            ),
        ],
    )
    def test_repr(self, vers: Version, expected: str) -> None:
        assert repr(vers) == expected

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (Version.from_str("1.2.3"), "1.2.3"),
            (Version.from_str("2024.03.14"), "2024.03.14"),
            (Version.from_str("3.4.5p8"), "3.4.5p8"),
            (Version.from_str("1.2.3-2024.09.09"), "1.2.3-2024.09.09"),
            (Version.from_str("2022.06.23-sandbox-az-sles-15sp3"), "2022.06.23"),
        ],
    )
    def test_str(self, vers: Version, expected: str) -> None:
        assert str(vers) == expected

    @pytest.mark.parametrize(
        "smaller, bigger",
        [
            (Version.from_str("1.2.0b1"), Version.from_str("1.2.0b2")),
            (Version.from_str("1.2.0i1"), Version.from_str("1.2.0i2")),
            (Version.from_str("1.2.0"), Version.from_str("1.2.0p1")),
            (Version.from_str("1.2.0p1"), Version.from_str("1.2.0p2")),
            (Version.from_str("1.2.0b1"), Version.from_str("1.2.0")),
            (Version.from_str("1.2.0"), Version.from_str("1.2.1")),
            (Version.from_str("1.2.3-2024.09.09"), Version.from_str("1.2.4-1970.01.01")),
            (Version.from_str("1.2.3"), Version.from_str("1.2.4")),
            (Version.from_str("2.0.0"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("2.0.0-2019.05.26"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("2.0.0-2020.04.26"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("2.0.0-2020.05.25"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("2.0.0b2"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("2.0.0i2"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("2.0.0p7"), Version.from_str("2.0.0-2020.05.26")),
            (Version.from_str("1.2.1"), Version.from_str("2.0.0")),
            (Version.from_str("2.0.0-2020.05.26"), Version.from_str("2.0.1-2020.05.26")),
            (Version.from_str("2.0.0-2020.05.25"), Version.from_str("2020.05.26")),
            (Version.from_str("2020.04.26"), Version.from_str("2020.05.26")),
            (Version.from_str("2020.05.25"), Version.from_str("2020.05.26")),
            (Version.from_str("2022.06.01"), Version.from_str("2022.06.02-sandbox-lm-2.2-thing")),
            (Version.from_str("2024.03.12"), Version.from_str("2024.03.14")),
            (Version.from_str("2.0.0-2020.05.26"), Version.from_str("2.1.0-2020.05.26")),
            (
                Version.from_str("2.1.0-2022.06.01"),
                Version.from_str("2.1.0-2022.06.02-sandbox-lm-2.2-thing"),
            ),
            (Version.from_str("3.4.5p8"), Version.from_str("3.5.5p4")),
        ],
    )
    def test_lt(self, smaller: Version, bigger: Version) -> None:
        assert smaller < bigger

    @pytest.mark.parametrize(
        "one, other, equal",
        [
            (Version.from_str("1.2.3"), Version.from_str("1.2.3"), True),
            (Version.from_str("1.2.3"), Version.from_str("1.3.3"), False),
            (Version.from_str("2024.03.14"), Version.from_str("2024.03.14"), True),
            (Version.from_str("2024.03.13"), Version.from_str("2024.03.14"), False),
            (Version.from_str("3.4.5p8"), Version.from_str("3.4.5p8"), True),
            (Version.from_str("3.4.5p8"), Version.from_str("3.4.5p7"), False),
            (Version.from_str("1.2.3-2024.09.09"), Version.from_str("1.2.3-2024.09.09"), True),
            (Version.from_str("1.2.3-2024.09.09"), Version.from_str("1.2.3-2024.09.19"), False),
            (Version.from_str("2024.03.13"), Version.from_str("3.4.5p8"), False),
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
        ("2020.05.26", 2020052690000),
        ("2022.06.23-sandbox-az-sles-15sp3", 2022062390000),
    ],
)
def test_parse_check_mk_version(version_string: str, expected: int) -> None:
    assert parse_check_mk_version(version_string) == expected


def test_omd_version_reads_from_version_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    link_path = tmp_path / "version"
    monkeypatch.setattr(cmk.utils.paths, "omd_root", link_path.parent)
    link_path.symlink_to("/omd/versions/2016.09.12.cee")
    # Is set dynamically by testlib.fake_version_and_paths
    assert cmk_version.orig_omd_version() == "2016.09.12.cee"  # type: ignore[attr-defined]
    link_path.unlink()
