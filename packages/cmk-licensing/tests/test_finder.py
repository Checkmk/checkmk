#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from importlib.metadata import EntryPoint, EntryPoints, PackagePath, PathDistribution
from pathlib import Path

import pytest

from cmk.licensing.basics import finder


class _FakeDistribution(PathDistribution):
    def __init__(self, entry_points: EntryPoints, files: list[PackagePath] | None) -> None:
        self._entry_points = entry_points
        self._files = files
        self._path = Path("/cmk_fake_package-3.14.15.dist-info")
        for f in self._files or []:
            f.dist = self

    @property
    def entry_points(self) -> EntryPoints:
        return self._entry_points

    @property
    def files(self) -> list[PackagePath] | None:
        return self._files

    @property
    def name(self) -> str:
        return "cmk-fake-package"


def _files(*paths: str) -> list[PackagePath]:
    return [PackagePath(p) for p in paths]


def _tags(*tags: str) -> EntryPoints:
    return EntryPoints(
        [EntryPoint(name="name", value="value", group=f"cmk.features.{t}") for t in tags]
    )


@pytest.fixture(name="fake_distributions")
def fixture_fake_distributions(
    monkeypatch: pytest.MonkeyPatch,
) -> list[_FakeDistribution]:
    dists: list[_FakeDistribution] = []
    monkeypatch.setattr(finder, "distributions", lambda: list(dists))
    return dists


def test_empty_disabled_set_returns_nothing(
    fake_distributions: list[_FakeDistribution],
) -> None:
    fake_distributions.append(
        _FakeDistribution(entry_points=_tags("bakery"), files=_files("/site/a/x.py")),
    )
    assert list(finder.files_for_disabled_features(set())) == []


def test_untagged_distributions_never_contribute(
    fake_distributions: list[_FakeDistribution],
) -> None:
    fake_distributions.extend(
        [
            _FakeDistribution(entry_points=EntryPoints(), files=_files("/site/stdlib/mod.py")),
            _FakeDistribution(entry_points=_tags("bakery"), files=_files("/site/b/x.py")),
        ]
    )
    assert list(finder.files_for_disabled_features({"bakery"})) == ["/site/b/x.py"]


def test_package_included_when_all_its_tags_are_disabled(
    fake_distributions: list[_FakeDistribution],
) -> None:
    fake_distributions.append(
        _FakeDistribution(
            entry_points=_tags("bakery", "reporting"),
            files=_files("/site/ccc/__init__.py", "/site/ccc/core.py"),
        ),
    )
    result = list(finder.files_for_disabled_features({"bakery", "reporting", "extra"}))
    assert sorted(result) == ["/site/ccc/__init__.py", "/site/ccc/core.py"]


def test_package_excluded_when_any_tag_still_enabled(
    fake_distributions: list[_FakeDistribution],
) -> None:
    # Package implements bakery AND reporting; reporting is NOT in the
    # disabled set, so the package still has an enabled feature and must
    # stay in the site.
    fake_distributions.append(
        _FakeDistribution(
            entry_points=_tags("bakery", "reporting"),
            files=_files("/site/ccc/x.py"),
        ),
    )
    assert not list(finder.files_for_disabled_features({"bakery"}))


def test_mixed_inclusion(fake_distributions: list[_FakeDistribution]) -> None:
    fake_distributions.extend(
        [
            _FakeDistribution(entry_points=_tags("bakery"), files=_files("/site/bk/a.py")),
            _FakeDistribution(
                entry_points=_tags("bakery", "reporting"),
                files=_files("/site/rb/a.py"),
            ),
            _FakeDistribution(entry_points=_tags("telemetry"), files=_files("/site/tl/a.py")),
            _FakeDistribution(entry_points=EntryPoints(), files=_files("/site/untagged/a.py")),
        ]
    )
    assert sorted(finder.files_for_disabled_features({"bakery", "reporting"})) == [
        "/site/bk/a.py",
        "/site/rb/a.py",
    ]


def test_missing_files_is_tolerated(fake_distributions: list[_FakeDistribution]) -> None:
    fake_distributions.extend(
        [
            _FakeDistribution(entry_points=_tags("bakery"), files=None),
            _FakeDistribution(entry_points=_tags("bakery"), files=_files("/site/good.py")),
        ]
    )
    assert list(finder.files_for_disabled_features({"bakery"})) == ["/site/good.py"]
