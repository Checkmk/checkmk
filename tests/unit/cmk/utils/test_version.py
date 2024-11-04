#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.version as cmk_version
from cmk.utils.version import parse_check_mk_version, Version


def test_version() -> None:
    assert isinstance(cmk_version.__version__, str)


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

    def test_master_daily_old_scheme(self) -> None:
        assert Version("2023.12.24")

    def test_invalid_vtype(self) -> None:
        with pytest.raises(ValueError):
            _version = Version("1.2.3g5")

    def test_invalid_combo(self) -> None:
        # currently invalid.
        with pytest.raises(ValueError):
            Version("1.2.3b5-2023.01.01")
        with pytest.raises(ValueError):
            Version("2.2.0rc1")
        with pytest.raises(ValueError):
            Version("2.2.0p5-rc")

    @pytest.mark.parametrize(
        "vers",
        [
            Version("2.3.0p34"),
            Version("2.3.0p34-rc42"),
            Version("2.3.0p34-rc42+security"),
            Version("1.2.3-2023.12.24"),
            Version("2023.12.24"),
        ],
    )
    def test_roundtrip(self, vers: Version) -> None:
        assert Version(str(vers)) == vers

    def test_version_base_master(self) -> None:
        assert Version("1984.04.01").version_base == ""

    def test_version_base_stable(self) -> None:
        assert Version("1.2.3").version_base == "1.2.3"

    def test_version_base_release(self) -> None:
        assert Version("4.5.6p8").version_base == "4.5.6"

    def test_version_release_candidate(self) -> None:
        assert Version("2.3.0b4-rc1").version.release_candidate == 1

    def test_version_without_rc_stable(self) -> None:
        assert Version("1.2.3").version_without_rc == "1.2.3"

    def test_version_without_rc_release(self) -> None:
        assert Version("4.5.6p8").version_without_rc == "4.5.6p8"

    def test_version_without_rc_release_candidate(self) -> None:
        assert Version("2.3.0b4-rc1").version_without_rc == "2.3.0b4"

    def test_version_rc_aware_stable(self) -> None:
        assert Version("1.2.3").version_rc_aware == "1.2.3"

    def test_version_rc_aware_release(self) -> None:
        assert Version("4.5.6p8").version_rc_aware == "4.5.6p8"

    def test_version_rc_aware_release_candidate(self) -> None:
        assert Version("2.3.0b4-rc1").version_rc_aware == "2.3.0b4-rc1"

    def test_version_meta_data(self) -> None:
        assert Version("2.3.0p21+security").version.meta == "security"

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (
                Version("1.2.3"),
                "_StableVersion(meta=None, release_candidate=None, major=1, minor=2, sub=3)",
            ),
            (
                Version("1.2.3+security"),
                "_StableVersion(meta='security', release_candidate=None, major=1, minor=2, sub=3)",
            ),
            (
                Version("1.2.3-rc7"),
                "_StableVersion(meta=None, release_candidate=7, major=1, minor=2, sub=3)",
            ),
            (
                Version("1.2.3-rc7+security"),
                "_StableVersion(meta='security', release_candidate=7, major=1, minor=2, sub=3)",
            ),
            (
                Version("2024.03.14"),
                "_MasterDailyVersion(date=datetime.date(2024, 3, 14))",
            ),
            (
                Version("3.4.5p8"),
                "_PatchVersion(meta=None, release_candidate=None, major=3, minor=4, sub=5, patch=8)",
            ),
            (
                Version("1.2.3-2024.09.09"),
                "_StableDailyVersion(major=1, minor=2, sub=3, date=datetime.date(2024, 9, 9))",
            ),
            (
                Version("2.2.0p5-rc1"),
                "_PatchVersion(meta=None, release_candidate=1, major=2, minor=2, sub=0, patch=5)",
            ),
            (
                Version("2.2.0p5-rc1+security"),
                "_PatchVersion(meta='security', release_candidate=1, major=2, minor=2, sub=0, patch=5)",
            ),
            (
                Version("2.2.0p5+security"),
                "_PatchVersion(meta='security', release_candidate=None, major=2, minor=2, sub=0, patch=5)",
            ),
        ],
    )
    def test_repr(self, vers: Version, expected: str) -> None:
        assert repr(vers.version) == expected

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (Version("1.2.3"), "1.2.3"),
            (Version("2024.03.14"), "2024.03.14"),
            (Version("3.4.5p8"), "3.4.5p8"),
            (Version("6.7.8p9-rc1"), "6.7.8p9-rc1"),
            (Version("6.7.8p9-rc1+security"), "6.7.8p9-rc1+security"),
            (Version("1.2.3-2024.09.09"), "1.2.3-2024.09.09"),
            (Version("2022.06.23-sandbox-az-sles-15sp3"), "2022.06.23"),
        ],
    )
    def test_str(self, vers: Version, expected: str) -> None:
        assert str(vers) == expected

    @pytest.mark.parametrize(
        "smaller, bigger",
        [
            (Version("1.2.0b1"), Version("1.2.0b2")),
            (Version("1.2.0i1"), Version("1.2.0i2")),
            (Version("1.2.0"), Version("1.2.0p1")),
            (Version("1.2.0p1"), Version("1.2.0p2")),
            (Version("1.2.0b1"), Version("1.2.0")),
            (Version("1.2.0"), Version("1.2.1")),
            (Version("1.2.3-2024.09.09"), Version("1.2.4-1970.01.01")),
            (Version("1.2.3"), Version("1.2.4")),
            (Version("2.0.0"), Version("2.0.0-2020.05.26")),
            (Version("2.0.0-2019.05.26"), Version("2.0.0-2020.05.26")),
            (Version("2.0.0-2020.04.26"), Version("2.0.0-2020.05.26")),
            (Version("2.0.0-2020.05.25"), Version("2.0.0-2020.05.26")),
            (Version("2.0.0b2"), Version("2.0.0-2020.05.26")),
            (Version("2.0.0i2"), Version("2.0.0-2020.05.26")),
            (Version("2.0.0p7"), Version("2.0.0-2020.05.26")),
            (Version("1.2.1"), Version("2.0.0")),
            (Version("2.0.0-2020.05.26"), Version("2.0.1-2020.05.26")),
            (Version("2.0.0-2020.05.25"), Version("2020.05.26")),
            (Version("2020.04.26"), Version("2020.05.26")),
            (Version("2020.05.25"), Version("2020.05.26")),
            (Version("2022.06.01"), Version("2022.06.02-sandbox-lm-2.2-thing")),
            (Version("2024.03.12"), Version("2024.03.14")),
            (Version("2.0.0-2020.05.26"), Version("2.1.0-2020.05.26")),
            (
                Version("2.1.0-2022.06.01"),
                Version("2.1.0-2022.06.02-sandbox-lm-2.2-thing"),
            ),
            (Version("3.4.5p8"), Version("3.5.5p4")),
            (Version("2.3.0p8-rc1"), Version("2.3.0p8-rc2")),
            # (Version("2.3.0p8-rc1"), Version("2.3.0p9")),
            (Version("2.3.0p8"), Version("2.3.0p9-rc1")),
            (Version("2.3.0p8"), Version("2.3.0p9+security")),
            (Version("2.3.0p8+security"), Version("2.3.0p9")),
            (Version("2.3.0p8-rc1+security"), Version("2.3.0p8-rc2+security")),
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
            (Version("2.3.0p5-rc2"), Version("2.3.0p5-rc2"), True),
            (Version("2.3.0p5-rc2"), Version("2.3.0p5-rc3"), False),
            (Version("2.3.0p5-rc3+security"), Version("2.3.0p5-rc3+security"), True),
            (
                Version("2.3.0p5-rc4+security"),
                Version("2.3.0p5-rc4"),
                True,  # https://semver.org/#spec-item-10, Build metadata MUST be ignored when determining version precedence
            ),
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
        ("2022.06.23-sandbox-az-sles-15sp3", 2022062300000),
    ],
)
def test_parse_check_mk_version(version_string: str, expected: int) -> None:
    assert parse_check_mk_version(version_string) == expected


class TestEdition:
    @pytest.mark.parametrize(
        "omd_version_str, expected",
        [
            ("1.4.0i1.cre", cmk_version.Edition.CRE),
            ("1.4.0i1.cee", cmk_version.Edition.CEE),
            ("2016.09.22.cee", cmk_version.Edition.CEE),
            ("2.1.0p3.cme", cmk_version.Edition.CME),
            ("2.1.0p3.cce", cmk_version.Edition.CCE),
        ],
    )
    def test_from_version_string(self, omd_version_str: str, expected: cmk_version.Edition) -> None:
        assert cmk_version.Edition.from_version_string(omd_version_str) is expected
