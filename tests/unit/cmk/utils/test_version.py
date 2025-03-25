#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

import cmk.ccc.version as cmk_version
from cmk.ccc.version import parse_check_mk_version, Version


def test_version() -> None:
    assert isinstance(cmk_version.__version__, str)


class TestVersion:
    def test_stable(self) -> None:
        Version.from_str("1.2.3")

    def test_innovation(self) -> None:
        Version.from_str("1.2.4i8")

    def test_beta(self) -> None:
        Version.from_str("1.2.4b1")

    def test_patch(self) -> None:
        Version.from_str("1.2.4p3")

    def test_stable_daily(self) -> None:
        Version.from_str("1.2.3-2023.12.24")

    def test_master_daily_old_scheme(self) -> None:
        Version.from_str("2023.12.24")

    def test_invalid_vtype(self) -> None:
        with pytest.raises(ValueError):
            Version.from_str("1.2.3g5")

    def test_invalid_combo(self) -> None:
        # currently invalid.
        with pytest.raises(ValueError):
            Version.from_str("1.2.3b5-2023.01.01")
        with pytest.raises(ValueError):
            Version.from_str("2.2.0rc1")
        with pytest.raises(ValueError):
            Version.from_str("2.2.0p5-rc")
        with pytest.raises(ValueError):
            Version.from_str("1.2.3-2023.12.24-rc1")
        with pytest.raises(ValueError):
            Version.from_str("2023.12.24-rc1")

    @pytest.mark.parametrize(
        "vers",
        [
            Version.from_str("2.3.0p34"),
            Version.from_str("2.3.0p34-rc42"),
            Version.from_str("2.3.0p34-rc42+security"),
            Version.from_str("1.2.3-2023.12.24"),
            Version.from_str("2023.12.24"),
        ],
    )
    def test_roundtrip(self, vers: Version) -> None:
        assert Version.from_str(str(vers)) == vers

    def test_version_base_master(self) -> None:
        assert Version.from_str("1984.04.01").version_base == ""

    def test_version_base_stable(self) -> None:
        assert Version.from_str("1.2.3").version_base == "1.2.3"

    def test_version_base_release(self) -> None:
        assert Version.from_str("4.5.6p8").version_base == "4.5.6"

    def test_version_base_stable_daily(self) -> None:
        assert Version.from_str("1.2.3-2023.12.24").version_base == "1.2.3"

    def test_version_release_candidate(self) -> None:
        assert Version.from_str("2.3.0b4-rc1").release_candidate.value == 1

    def test_version_meta_data(self) -> None:
        assert Version.from_str("2.3.0p21+security").meta.value == "security"

    def test_version_without_rc_master(self) -> None:
        assert Version.from_str("1984.04.01").version_without_rc == "1984.04.01"

    def test_version_without_rc_stable(self) -> None:
        assert Version.from_str("1.2.3").version_without_rc == "1.2.3"

    def test_version_without_rc_release(self) -> None:
        assert Version.from_str("4.5.6p8").version_without_rc == "4.5.6p8"

    def test_version_without_rc_release_candidate(self) -> None:
        assert Version.from_str("2.3.0b4-rc1").version_without_rc == "2.3.0b4"

    def test_version_without_rc_stable_daily(self) -> None:
        assert Version.from_str("1.2.3-2023.12.24").version_without_rc == "1.2.3-2023.12.24"

    def test_version_rc_aware_master(self) -> None:
        assert Version.from_str("1984.04.01").version_rc_aware == "1984.04.01"

    def test_version_rc_aware_stable(self) -> None:
        assert Version.from_str("1.2.3").version_rc_aware == "1.2.3"

    def test_version_rc_aware_stable_release_candidate(self) -> None:
        assert Version.from_str("1.2.3-rc1").version_rc_aware == "1.2.3-rc1"

    def test_version_rc_aware_release(self) -> None:
        assert Version.from_str("4.5.6p8").version_rc_aware == "4.5.6p8"

    def test_version_rc_aware_release_candidate(self) -> None:
        assert Version.from_str("2.3.0b4-rc1").version_rc_aware == "2.3.0b4-rc1"

    def test_version_rc_aware_stable_daily(self) -> None:
        assert Version.from_str("1.2.3-2023.12.24").version_rc_aware == "1.2.3-2023.12.24"

    @pytest.mark.parametrize(
        "vers, expected",
        [
            (
                Version.from_str("1.2.3"),
                "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.na, value=0), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))",
            ),
            (
                Version.from_str("1.2.3+security"),
                "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.na, value=0), _ReleaseCandidate(value=None), _ReleaseMeta(value='security'))",
            ),
            (
                Version.from_str("1.2.3-rc7"),
                "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.na, value=0), _ReleaseCandidate(value=7), _ReleaseMeta(value=None))",
            ),
            (
                Version.from_str("2024.03.14"),
                "Version(None, _Release(release_type=ReleaseType.daily, value=BuildDate(year=2024, month=3, day=14)), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))",
            ),
            (
                Version.from_str("3.4.5p8"),
                "Version(_BaseVersion(major=3, minor=4, sub=5), _Release(release_type=ReleaseType.p, value=8), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))",
            ),
            (
                Version.from_str("1.2.3-2024.09.09"),
                "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.daily, value=BuildDate(year=2024, month=9, day=9)), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))",
            ),
            (
                Version.from_str("2.2.0p5-rc1"),
                "Version(_BaseVersion(major=2, minor=2, sub=0), _Release(release_type=ReleaseType.p, value=5), _ReleaseCandidate(value=1), _ReleaseMeta(value=None))",
            ),
            (
                Version.from_str("2.2.0p5-rc1+security"),
                "Version(_BaseVersion(major=2, minor=2, sub=0), _Release(release_type=ReleaseType.p, value=5), _ReleaseCandidate(value=1), _ReleaseMeta(value='security'))",
            ),
            (
                Version.from_str("2.2.0p5+security"),
                "Version(_BaseVersion(major=2, minor=2, sub=0), _Release(release_type=ReleaseType.p, value=5), _ReleaseCandidate(value=None), _ReleaseMeta(value='security'))",
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
            (Version.from_str("6.7.8p9-rc1"), "6.7.8p9-rc1"),
            (Version.from_str("6.7.8p9-rc1+security"), "6.7.8p9-rc1+security"),
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
            (Version.from_str("2.3.0p8-rc1"), Version.from_str("2.3.0p8-rc2")),
            (Version.from_str("2.3.0p8-rc1"), Version.from_str("2.3.0p9")),
            (Version.from_str("2.3.0p8"), Version.from_str("2.3.0p9-rc1")),
            (Version.from_str("2.3.0p8"), Version.from_str("2.3.0p9+security")),
            (Version.from_str("2.3.0p8+security"), Version.from_str("2.3.0p9")),
            (Version.from_str("2.3.0p8-rc1+security"), Version.from_str("2.3.0p8-rc2+security")),
        ],
    )
    def test_lt(self, smaller: Version, bigger: Version) -> None:
        assert smaller < bigger

    def test_lt_unknown(self) -> None:
        with pytest.raises(ValueError):
            _ = Version.from_str("2.3.0p8-rc1") < Version.from_str("2.3.0p8")

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
            (Version.from_str("2.3.0p5-rc2"), Version.from_str("2.3.0p5-rc2"), True),
            (Version.from_str("2.3.0p5-rc2"), Version.from_str("2.3.0p5-rc3"), False),
            (
                Version.from_str("2.3.0p5-rc3+security"),
                Version.from_str("2.3.0p5-rc3+security"),
                True,
            ),
            (
                Version.from_str("2.3.0p5-rc4+security"),
                Version.from_str("2.3.0p5-rc4"),
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
        ("2022.06.23-sandbox-az-sles-15sp3", 2022062390000),
    ],
)
def test_parse_check_mk_version(version_string: str, expected: int) -> None:
    assert parse_check_mk_version(version_string) == expected


def test_omd_version_reads_from_version_link(tmp_path: Path) -> None:
    link_path = tmp_path / "version"
    link_path.symlink_to("/omd/versions/2016.09.12.cee")
    # Is set dynamically by fake_version_and_paths
    assert cmk_version.orig_omd_version(link_path.parent) == "2016.09.12.cee"  # type: ignore[attr-defined]
    link_path.unlink()


class TestEdition:
    @pytest.mark.parametrize(
        "omd_version_str, expected",
        [
            ("1.4.0i1.cre", cmk_version.Edition.CRE),
            ("1.4.0i1.cee", cmk_version.Edition.CEE),
            ("2016.09.22.cee", cmk_version.Edition.CEE),
            ("2.1.0p3.cme", cmk_version.Edition.CME),
            ("2.1.0p3.cce", cmk_version.Edition.CCE),
            ("2.1.0p3.cse", cmk_version.Edition.CSE),
        ],
    )
    def test_from_version_string(self, omd_version_str: str, expected: cmk_version.Edition) -> None:
        assert cmk_version.Edition.from_version_string(omd_version_str) is expected
