#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.mkp_tool._type_defs import PackageName, PackageVersion


class TestPackageVersion:
    def test_sort_key_semver_simple(self) -> None:
        assert PackageVersion("1.2.3").sort_key < PackageVersion("1.2.4").sort_key

    def test_sort_key_semver_prerelease(self) -> None:
        # Pre-release versions have a lower precedence than the associated normal version.
        assert PackageVersion("1.2.3-alpha").sort_key < PackageVersion("1.2.3").sort_key
        # Identifiers consisting of only digits are compared numerically.
        assert PackageVersion("1.2.3-3").sort_key < PackageVersion("1.2.3-12").sort_key
        # Identifiers with letters or hyphens are compared lexically in ASCII sort order.
        assert PackageVersion("1.2.3-alpha").sort_key < PackageVersion("1.2.3-beta").sort_key
        # Numeric identifiers always have lower precedence than non-numeric identifiers.
        assert PackageVersion("1.2.3-alpha").sort_key < PackageVersion("1.2.3-1").sort_key
        # A larger set of pre-release fields has a higher precedence than a smaller set,
        # if all of the preceding identifiers are equal.
        assert (
            PackageVersion("1.2.3-alpha.beta.wurstbrot").sort_key
            < PackageVersion("1.2.3-alpha.beta").sort_key
        )

    def test_sort_key_semver_ignores_build_metadata(self) -> None:
        # Build metadata MUST be ignored when determining version precedence.
        assert (
            PackageVersion("1.2.3-kaese+x64").sort_key
            == PackageVersion("1.2.3-kaese+sparc").sort_key
        )

    def test_sort_key_additional_bs(self) -> None:
        # proper versions are newer than BS
        assert PackageVersion("wt🐟?").sort_key < PackageVersion("0").sort_key
        assert PackageVersion("v1.2").sort_key < PackageVersion("v1.3").sort_key

        # this is not correct, but we don't care:
        assert PackageVersion("v2").sort_key > PackageVersion("v10").sort_key

    @pytest.mark.parametrize("raw_str", ["1/2/3", "/", "1.2.3/"])
    def test_invalid_version(self, raw_str: str) -> None:
        with pytest.raises(ValueError, match="must not contain slashes"):
            _ = PackageVersion(raw_str)

    @pytest.mark.parametrize(
        "raw_str",
        [
            "1.2.3",
            "0.0.0",
            "1.2.3-alpha",
            "1.2.3-alpha.1",
            "1.2.3+build.42",
            "1.2.3-beta.2+x64",
        ],
    )
    def test_parse_semver(self, raw_str: str) -> None:
        assert PackageVersion.parse_semver(raw_str) == raw_str

    @pytest.mark.parametrize(
        "raw_str",
        [
            "",
            "1",
            "1.2",
            "1.2.3.4",
            "01.2.3",
            "v1.2.3",
            "1.2.3-",
        ],
    )
    def test_parse_semver_invalid(self, raw_str: str) -> None:
        with pytest.raises(ValueError, match="Not a valid semantic versioning string"):
            _ = PackageVersion.parse_semver(raw_str)


@pytest.mark.parametrize("raw_str", ["", "foo;bar"])
def test_invalid_name(raw_str: str) -> None:
    with pytest.raises(ValueError, match=raw_str):
        _ = PackageName(raw_str)
