#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

import cmk.ccc.version as cmk_version
from cmk.ccc.version import parse_check_mk_version, Version, versions_compatible


class TestVersion:
    @pytest.mark.parametrize(
        "version_string",
        [
            pytest.param("1.2.3", id="stable"),
            pytest.param("1.2.4i8", id="innovation"),
            pytest.param("1.2.4b1", id="beta"),
            pytest.param("1.2.4p3", id="patch"),
            pytest.param("1.2.3-2023.12.24", id="stable daily"),
            pytest.param("2023.12.24", id="master daily old scheme"),
        ],
    )
    def test_valid_version_string_parses(self, version_string: str) -> None:
        Version.from_str(version_string)

    @pytest.mark.parametrize(
        "version_string",
        [
            pytest.param("1.2.3g5", id="unknown release type"),
            pytest.param("1.2.3b5-2023.01.01", id="beta with date suffix"),
            pytest.param("2.2.0rc1", id="rc without patch level"),
            pytest.param("2.2.0p5-rc", id="patch with bare rc suffix"),
            pytest.param("1.2.3-2023.12.24-rc1", id="stable daily with rc suffix"),
            pytest.param("2023.12.24-rc1", id="daily with rc suffix"),
        ],
    )
    def test_invalid_version_string_raises(self, version_string: str) -> None:
        with pytest.raises(ValueError):
            Version.from_str(version_string)

    @pytest.mark.parametrize(
        "version_string",
        [
            pytest.param("2.3.0p34", id="patch"),
            pytest.param("2.3.0p34-rc42", id="release candidate"),
            pytest.param("2.3.0p34-rc42+security", id="release candidate with metadata"),
            pytest.param("1.2.3-2023.12.24", id="branch daily"),
            pytest.param("2023.12.24", id="master daily old scheme"),
        ],
    )
    def test_str_parses_back_to_the_same_version(self, version_string: str) -> None:
        version = Version.from_str(version_string)

        assert Version.from_str(str(version)) == version

    @pytest.mark.parametrize(
        "version_string, expected",
        [
            pytest.param("1984.04.01", "", id="master daily"),
            pytest.param("1.2.3", "1.2.3", id="stable"),
            pytest.param("4.5.6p8", "4.5.6", id="patch release"),
            pytest.param("1.2.3-2023.12.24", "1.2.3", id="stable daily"),
        ],
    )
    def test_version_base_is_the_branch_version(self, version_string: str, expected: str) -> None:
        assert Version.from_str(version_string).version_base == expected

    def test_release_candidate_is_the_number_after_rc(self) -> None:
        assert Version.from_str("2.3.0b4-rc1").release_candidate.value == 1

    def test_meta_data_is_the_part_after_the_plus(self) -> None:
        assert Version.from_str("2.3.0p21+security").meta.value == "security"

    @pytest.mark.parametrize(
        "version_string, expected",
        [
            pytest.param("1984.04.01", "1984.04.01", id="master daily"),
            pytest.param("1.2.3", "1.2.3", id="stable"),
            pytest.param("4.5.6p8", "4.5.6p8", id="patch release"),
            pytest.param("2.3.0b4-rc1", "2.3.0b4", id="release candidate"),
            pytest.param("1.2.3-2023.12.24", "1.2.3-2023.12.24", id="stable daily"),
            pytest.param(
                "1.2.3-2023.12.24.ultimate", "1.2.3-2023.12.24", id="stable daily with edition"
            ),
        ],
    )
    def test_version_without_rc_leaves_out_release_candidate_and_edition(
        self, version_string: str, expected: str
    ) -> None:
        assert Version.from_str(version_string).version_without_rc == expected

    @pytest.mark.parametrize(
        "version_string",
        [
            pytest.param("1984.04.01", id="master daily"),
            pytest.param("1.2.3", id="stable"),
            pytest.param("1.2.3-rc1", id="stable release candidate"),
            pytest.param("4.5.6p8", id="patch release"),
            pytest.param("2.3.0b4-rc1", id="release candidate"),
            pytest.param("1.2.3-2023.12.24", id="stable daily"),
        ],
    )
    def test_version_rc_aware_keeps_the_release_candidate(self, version_string: str) -> None:
        assert Version.from_str(version_string).version_rc_aware == version_string

    @pytest.mark.parametrize(
        "version_string, expected",
        [
            pytest.param("1.2.3", "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.na, value=0), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))", id="stable"),
            pytest.param("1.2.3+security", "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.na, value=0), _ReleaseCandidate(value=None), _ReleaseMeta(value='security'))", id="stable with metadata"),
            pytest.param("1.2.3-rc7", "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.na, value=0), _ReleaseCandidate(value=7), _ReleaseMeta(value=None))", id="stable release candidate"),
            pytest.param("2024.03.14", "Version(None, _Release(release_type=ReleaseType.daily, value=BuildDate(year=2024, month=3, day=14)), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))", id="master daily"),
            pytest.param("3.4.5p8", "Version(_BaseVersion(major=3, minor=4, sub=5), _Release(release_type=ReleaseType.p, value=8), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))", id="patch"),
            pytest.param("1.2.3-2024.09.09", "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.daily, value=BuildDate(year=2024, month=9, day=9)), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))", id="branch daily"),
            pytest.param("1.2.3-2023.12.24.ultimate", "Version(_BaseVersion(major=1, minor=2, sub=3), _Release(release_type=ReleaseType.daily, value=BuildDate(year=2023, month=12, day=24)), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))", id="branch daily with edition"),
            pytest.param("2.2.0p5-rc1", "Version(_BaseVersion(major=2, minor=2, sub=0), _Release(release_type=ReleaseType.p, value=5), _ReleaseCandidate(value=1), _ReleaseMeta(value=None))", id="patch release candidate"),
            pytest.param("2.2.0p5-rc1+security", "Version(_BaseVersion(major=2, minor=2, sub=0), _Release(release_type=ReleaseType.p, value=5), _ReleaseCandidate(value=1), _ReleaseMeta(value='security'))", id="patch release candidate with metadata"),
            pytest.param("2.2.0p5+security", "Version(_BaseVersion(major=2, minor=2, sub=0), _Release(release_type=ReleaseType.p, value=5), _ReleaseCandidate(value=None), _ReleaseMeta(value='security'))", id="patch with metadata"),
        ],
    )  # fmt: skip
    def test_repr_shows_all_parts(self, version_string: str, expected: str) -> None:
        assert repr(Version.from_str(version_string)) == expected

    @pytest.mark.parametrize(
        "version_string, expected",
        [
            pytest.param("1.2.3", "1.2.3", id="stable"),
            pytest.param("2024.03.14", "2024.03.14", id="master daily"),
            pytest.param("3.4.5p8", "3.4.5p8", id="patch"),
            pytest.param("6.7.8p9-rc1", "6.7.8p9-rc1", id="release candidate"),
            pytest.param("6.7.8p9-rc1+security", "6.7.8p9-rc1+security", id="metadata"),
            pytest.param("1.2.3-2024.09.09", "1.2.3-2024.09.09", id="branch daily"),
            pytest.param("2022.06.23-sandbox-az-sles-15sp3", "2022.06.23", id="sandbox build"),
        ],
    )
    def test_str_is_the_canonical_version_string(self, version_string: str, expected: str) -> None:
        assert str(Version.from_str(version_string)) == expected

    @pytest.mark.parametrize(
        "older, newer",
        [
            pytest.param("1.2.0b1", "1.2.0b2", id="betas"),
            pytest.param("1.2.0i1", "1.2.0i2", id="innovation releases"),
            pytest.param("1.2.0", "1.2.0p1", id="stable before its patch"),
            pytest.param("1.2.0p1", "1.2.0p2", id="patches"),
            pytest.param("1.2.0b1", "1.2.0", id="beta before stable"),
            pytest.param("1.2.0", "1.2.1", id="sub versions"),
            pytest.param("1.2.3-2024.09.09", "1.2.4-1970.01.01", id="branch dailies by base first"),
            pytest.param("1.2.3", "1.2.4", id="sub versions of stables"),
            pytest.param("2.0.0", "2.0.0-2020.05.26", id="stable before branch daily"),
            pytest.param("2.0.0-2019.05.26", "2.0.0-2020.05.26", id="branch dailies by year"),
            pytest.param("2.0.0-2020.04.26", "2.0.0-2020.05.26", id="branch dailies by month"),
            pytest.param("2.0.0-2020.05.25", "2.0.0-2020.05.26", id="branch dailies by day"),
            pytest.param("2.0.0b2", "2.0.0-2020.05.26", id="beta before branch daily"),
            pytest.param("2.0.0i2", "2.0.0-2020.05.26", id="innovation before branch daily"),
            pytest.param("2.0.0p7", "2.0.0-2020.05.26", id="patch before branch daily"),
            pytest.param("1.2.1", "2.0.0", id="major versions"),
            pytest.param("2.0.0-2020.05.26", "2.0.1-2020.05.26", id="branch dailies by sub version"),
            pytest.param("2.0.0-2020.05.25", "2020.05.26", id="branch daily before master daily"),
            pytest.param("2020.04.26", "2020.05.26", id="master dailies by month"),
            pytest.param("2020.05.25", "2020.05.26", id="master dailies by day"),
            pytest.param("2022.06.01", "2022.06.02-sandbox-lm-2.2-thing", id="sandbox build"),
            pytest.param("2024.03.12", "2024.03.14", id="master dailies days apart"),
            pytest.param("2.0.0-2020.05.26", "2.1.0-2020.05.26", id="branch dailies by minor"),
            pytest.param("2.1.0-2022.06.01", "2.1.0-2022.06.02-sandbox-lm-2.2-thing", id="branch sandbox build"),
            pytest.param("3.4.5p8", "3.5.5p4", id="minor before patch"),
            pytest.param("2.3.0p8-rc1", "2.3.0p8-rc2", id="release candidates"),
            pytest.param("2.3.0p8-rc1", "2.3.0p9", id="candidate before next patch"),
            pytest.param("2.3.0p8", "2.3.0p9-rc1", id="patch before next candidate"),
            pytest.param("2.3.0p8", "2.3.0p9+security", id="patch before next with metadata"),
            pytest.param("2.3.0p8+security", "2.3.0p9", id="patch with metadata before next"),
            pytest.param("2.3.0p8-rc1+security", "2.3.0p8-rc2+security", id="candidates with metadata"),
        ],
    )  # fmt: skip
    def test_older_version_is_less(self, older: str, newer: str) -> None:
        assert Version.from_str(older) < Version.from_str(newer)

    def test_comparing_a_release_candidate_with_its_release_raises(self) -> None:
        with pytest.raises(ValueError):
            _ = Version.from_str("2.3.0p8-rc1") < Version.from_str("2.3.0p8")

    @pytest.mark.parametrize(
        "one, other",
        [
            pytest.param("1.2.3", "1.2.3", id="stable"),
            pytest.param("2024.03.14", "2024.03.14", id="master daily"),
            pytest.param("3.4.5p8", "3.4.5p8", id="patch"),
            pytest.param("1.2.3-2024.09.09", "1.2.3-2024.09.09", id="branch daily"),
            pytest.param("2.3.0p5-rc2", "2.3.0p5-rc2", id="release candidate"),
            pytest.param("2.3.0p5-rc3+security", "2.3.0p5-rc3+security", id="metadata"),
            # https://semver.org/#spec-item-10, Build metadata MUST be ignored when determining version precedence
            pytest.param("2.3.0p5-rc4+security", "2.3.0p5-rc4", id="metadata ignored"),
        ],
    )
    def test_same_versions_are_equal(self, one: str, other: str) -> None:
        assert Version.from_str(one) == Version.from_str(other)

    @pytest.mark.parametrize(
        "one, other",
        [
            pytest.param("1.2.3", "1.3.3", id="minor versions"),
            pytest.param("2024.03.13", "2024.03.14", id="master dailies"),
            pytest.param("3.4.5p8", "3.4.5p7", id="patches"),
            pytest.param("1.2.3-2024.09.09", "1.2.3-2024.09.19", id="branch dailies"),
            pytest.param("2024.03.13", "3.4.5p8", id="master daily and patch"),
            pytest.param("2.3.0p5-rc2", "2.3.0p5-rc3", id="release candidates"),
        ],
    )
    def test_different_versions_are_not_equal(self, one: str, other: str) -> None:
        assert Version.from_str(one) != Version.from_str(other)


@pytest.mark.parametrize(
    "version_string, expected",
    [
        pytest.param("1.5.0-2019.10.10", 1050090000, id="branch daily"),
        pytest.param("1.6.0-2019.10.10", 1060090000, id="branch daily of next minor"),
        pytest.param("1.5.0-2019.10.24", 1050090000, id="branch daily of another day"),
        pytest.param("1.5.0-2018.05.05", 1050090000, id="branch daily of another year"),
        pytest.param("1.2.4p1", 1020450001, id="patch"),
        pytest.param("1.2.4", 1020450000, id="stable"),
        pytest.param("1.2.4b1", 1020420100, id="beta"),
        pytest.param("1.2.3p1", 1020350001, id="patch of previous sub version"),
        pytest.param("1.2.3i1", 1020310100, id="innovation release"),
        pytest.param("1.2.3i1p1", 1020310101, id="patch of innovation release"),
        pytest.param("1.2.4p10", 1020450010, id="two-digit patch"),
        pytest.param("1.5.0p22", 1050050022, id="patch of later minor"),
        pytest.param("2020.05.26", 2020052690000, id="master daily"),
        pytest.param("2022.06.23-sandbox-az-sles-15sp3", 2022062390000, id="sandbox build"),
        # No real Checkmk versions, but the parsing has to stay lenient for the
        # rules of "Checkmk Agent installation auditing".
        pytest.param("1.2", 1020050000, id="two parts"),
        pytest.param("1.2.3i12p4b43", 1020315504, id="several release types"),
    ],
)
def test_parsed_versions_keep_their_integer_encoding(version_string: str, expected: int) -> None:
    assert parse_check_mk_version(version_string) == expected


@pytest.mark.parametrize(
    "older, newer",
    [
        pytest.param("1.5.0", "1.5.0p22", id="stable before patch"),
        pytest.param("1.5.0p12", "1.5.0p13", id="patches"),
        pytest.param("1.5.0p22", "1.5.0-2019.10.10", id="patch before branch daily"),
    ],
)
def test_parsed_versions_keep_their_order(older: str, newer: str) -> None:
    assert parse_check_mk_version(older) < parse_check_mk_version(newer)


@pytest.mark.parametrize(
    "from_version, to_version",
    [
        pytest.param("2.0.0i1", "2021.12.13", id="to old-scheme master daily"),
        pytest.param("2021.12.13", "2.0.0i1", id="from old-scheme master daily"),
        pytest.param("2021.12.13", "2022.01.01", id="newer old-scheme master daily"),
        pytest.param("2022.01.01", "2021.12.13", id="older old-scheme master daily"),
        pytest.param("2.0.0-2022.01.01", "2.0.0p3", id="from branch daily"),
        pytest.param("2.0.0p3", "2.0.0-2022.01.01", id="to branch daily"),
        pytest.param("2.0.0i1", "2.0.0p3", id="newer in same major"),
        pytest.param("2.0.0p3", "2.0.0i1", id="older in same major"),
        pytest.param("2.0.0p3", "2.0.0p3", id="same version"),
        pytest.param("1.6.0i1", "2.0.0", id="next major after 1.6.0i1"),
        pytest.param("1.6.0p23", "2.0.0", id="next major after 1.6.0p23"),
        pytest.param("2.0.0p12", "2.1.0i1", id="next major after 2.0.0p12"),
        pytest.param("2.2.0p8", "2.3.0i1", id="next major after required patch release"),
        pytest.param("2.5.0p999", "3.0.0", id="3.0.0 after a 2.5.0 patch release"),
    ],
)
def test_versions_are_compatible(from_version: str, to_version: str) -> None:
    result = versions_compatible(Version.from_str(from_version), Version.from_str(to_version))

    assert result.is_compatible, str(result)


_TOO_NEW = "Target version too new (one major version jump at maximum)."
_TOO_OLD = "Target version too old (older major version is not supported)."
_REQUIRES = "This target version requires at least "


@pytest.mark.parametrize(
    "from_version, to_version, reason",
    [
        pytest.param("1.6.0p1", "2.1.0p3", _TOO_NEW, id="two majors up"),
        pytest.param("1.6.0p1", "2.1.0b1", _TOO_NEW, id="two majors up to a beta"),
        pytest.param("1.5.0i1", "2.0.0", _TOO_NEW, id="two majors up to a new first number"),
        pytest.param("1.4.0", "2.0.0", _TOO_NEW, id="three majors up to a new first number"),
        pytest.param("2.0.0", "1.6.0p1", _TOO_OLD, id="previous major"),
        pytest.param("2.1.0", "2.0.0b1", _TOO_OLD, id="previous major beta"),
        pytest.param("2.2.0b1000", "2.3.0i1", _REQUIRES + "2.2.0p8", id="before required patch"),
        pytest.param("2.4.0p5", "3.0.0", _TOO_NEW, id="3.0.0 after 2.4.0"),
        pytest.param("2.3.0", "2.5.0", _TOO_NEW, id="two majors up within 2.x"),
        pytest.param("1.6.0", "3.0.0", _TOO_NEW, id="two first numbers up"),
        pytest.param("2.5.0", "2.5.1", _TOO_NEW, id="sub version up"),
    ],
)
def test_incompatible_versions_tell_why(from_version: str, to_version: str, reason: str) -> None:
    result = versions_compatible(Version.from_str(from_version), Version.from_str(to_version))

    assert not result.is_compatible
    assert str(result) == reason


def test_updating_a_beta_to_the_next_major_needs_its_release() -> None:
    result = versions_compatible(Version.from_str("2.5.0b1"), Version.from_str("3.0.0"))

    assert not result.is_compatible
    assert str(result).startswith(_REQUIRES + "2.5.0")


def test_omd_version_reads_from_version_link(tmp_path: Path) -> None:
    link_path = tmp_path / "version"
    link_path.symlink_to("/omd/versions/2016.09.12.pro")

    assert cmk_version.omd_version(link_path.parent) == "2016.09.12.pro"


class TestEdition:
    @pytest.mark.parametrize(
        "omd_version_str, expected",
        [
            pytest.param("1.4.0i1.community", cmk_version.Edition.COMMUNITY, id="community"),
            pytest.param("1.4.0i1.pro", cmk_version.Edition.PRO, id="pro"),
            pytest.param("2016.09.22.pro", cmk_version.Edition.PRO, id="pro master daily"),
            pytest.param("2.1.0p3.ultimatemt", cmk_version.Edition.ULTIMATEMT, id="ultimatemt"),
            pytest.param("2.1.0p3.ultimate", cmk_version.Edition.ULTIMATE, id="ultimate"),
            pytest.param("2.1.0p3.cloud", cmk_version.Edition.CLOUD, id="cloud"),
        ],
    )
    def test_edition_comes_from_the_version_suffix(
        self, omd_version_str: str, expected: cmk_version.Edition
    ) -> None:
        assert cmk_version.Edition.from_version_string(omd_version_str) is expected
