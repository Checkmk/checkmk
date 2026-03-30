# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.types (Edition enum and SiteInfo dataclass)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from cmk.dev_deploy.types import Edition, SiteInfo


@pytest.mark.parametrize(
    "suffix,expected",
    [
        ("community", Edition.COMMUNITY),
        ("pro", Edition.PRO),
        ("ultimate", Edition.ULTIMATE),
        ("ultimatemt", Edition.ULTIMATEMT),
        ("cloud", Edition.CLOUD),
    ],
)
def test_edition_from_version_suffix_valid(suffix: str, expected: Edition) -> None:
    """All 5 valid suffixes parse to the correct Edition member."""
    assert Edition.from_version_suffix(suffix) is expected


def test_edition_from_version_suffix_invalid() -> None:
    """Unknown suffix raises ValueError with descriptive message."""
    with pytest.raises(ValueError, match="Unknown edition suffix"):
        Edition.from_version_suffix("enterprise")


@pytest.mark.parametrize("old_suffix", ["cre", "cee", "cce"])
def test_edition_from_version_suffix_old_style(old_suffix: str) -> None:
    """Old-style suffixes from pre-2.6.0 naming raise ValueError."""
    with pytest.raises(ValueError, match="Unknown edition suffix"):
        Edition.from_version_suffix(old_suffix)


def test_siteinfo_frozen() -> None:
    """SiteInfo is immutable -- assigning to a field raises FrozenInstanceError."""
    site = SiteInfo(
        name="v260",
        root=Path("/omd/sites/v260"),
        edition=Edition.PRO,
        version_string="2.6.0-2026.02.13.pro",
        build_commit="a" * 40,
    )
    with pytest.raises(FrozenInstanceError):
        site.name = "other"  # type: ignore[misc]


def test_siteinfo_with_commit() -> None:
    """SiteInfo with build_commit set carries all fields correctly."""
    commit = "abcdef1234567890abcdef1234567890abcdef12"
    site = SiteInfo(
        name="v260",
        root=Path("/omd/sites/v260"),
        edition=Edition.PRO,
        version_string="2.6.0-2026.02.13.pro",
        build_commit=commit,
    )
    assert site.name == "v260"
    assert site.root == Path("/omd/sites/v260")
    assert site.edition is Edition.PRO
    assert site.version_string == "2.6.0-2026.02.13.pro"
    assert site.build_commit == commit


def test_siteinfo_without_commit() -> None:
    """SiteInfo with build_commit=None is valid (older sites lack COMMIT file)."""
    site = SiteInfo(
        name="stable",
        root=Path("/omd/sites/stable"),
        edition=Edition.COMMUNITY,
        version_string="2.6.0-2026.01.01.community",
        build_commit=None,
    )
    assert site.name == "stable"
    assert site.edition is Edition.COMMUNITY
    assert site.build_commit is None


class TestEditionMatches:
    """Tests for Edition.matches() method."""

    @pytest.mark.parametrize("edition", list(Edition))
    def test_none_constraint_matches_all_editions(self, edition: Edition) -> None:
        assert edition.matches(None) is True

    def test_matching_single_constraint(self) -> None:
        assert Edition.PRO.matches(("pro",)) is True

    def test_non_matching_single_constraint(self) -> None:
        assert Edition.COMMUNITY.matches(("pro",)) is False

    def test_multi_value_constraint_match(self) -> None:
        assert Edition.ULTIMATE.matches(("pro", "ultimate")) is True

    def test_multi_value_constraint_no_match(self) -> None:
        assert Edition.CLOUD.matches(("pro", "ultimate")) is False

    @pytest.mark.parametrize(
        "constraint,edition,expected",
        [
            (("community",), Edition.COMMUNITY, True),
            (("community",), Edition.PRO, False),
            (("pro",), Edition.PRO, True),
            (("ultimate",), Edition.ULTIMATE, True),
            (("ultimatemt",), Edition.ULTIMATEMT, True),
            (("cloud",), Edition.CLOUD, True),
        ],
    )
    def test_all_five_editions(
        self,
        constraint: tuple[str, ...],
        edition: Edition,
        expected: bool,
    ) -> None:
        assert edition.matches(constraint) is expected
