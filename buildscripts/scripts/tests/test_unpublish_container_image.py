#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib.util
from collections.abc import Iterator, Sequence
from pathlib import Path
from types import ModuleType
from typing import override

import pytest

from buildscripts.scripts.lib.registry import Credentials, DockerImage, Registry


def _load_script() -> ModuleType:
    path = Path(__file__).parent.parent / "unpublish-container-image.py"
    spec = importlib.util.spec_from_file_location("unpublish_container_image", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="script", scope="module")
def fixture_script() -> ModuleType:
    return _load_script()


class _FakeRegistry(Registry):
    """A registry with recorded state instead of a docker daemon behind it."""

    def __init__(
        self,
        editions: Sequence[str],
        existing: Sequence[str],
        tags: dict[str, Sequence[str]],
        previous_release: str = "2.3.0p23",
    ) -> None:
        self.editions = editions
        self.url = "https://hub.docker.com/"
        self.credentials = Credentials("user", "secret")
        self.existing = set(existing)
        self.tags = tags
        self.previous_release = previous_release
        self.moved_tags: list[tuple[str, str]] = []
        self.deleted: list[str] = []
        self.image_exists = lambda image, _edition: image.full_name() in self.existing
        self.get_image_tags = lambda _image_name: iter(())

    @override
    def get_all_image_tags(self, image: DockerImage) -> tuple[str, ...]:
        return tuple(self.tags.get(image.full_name(), ()))

    @override
    def get_previous_release_tag(self, _image: DockerImage, _edition: str) -> str:
        return self.previous_release

    @override
    def tag(self, source: str, new_tag: str) -> None:
        self.moved_tags.append((source, new_tag))

    @override
    def delete_image(self, image: DockerImage) -> None:
        self.deleted.append(image.full_name())

    @override
    def list_images(self, _image_name: str) -> Iterator[DockerImage]:
        yield from ()


@pytest.mark.parametrize(
    "tag, expected",
    [
        pytest.param("latest", True, id="plain latest"),
        pytest.param("2.3.0-latest", True, id="branch latest"),
        pytest.param("2.3.0p24", False, id="patch release"),
    ],
)
def test_is_latest_recognizes_latest_tags(script: ModuleType, tag: str, expected: bool) -> None:
    assert script.is_latest(tag) is expected


@pytest.mark.parametrize(
    "edition, expected",
    [
        pytest.param("community", "checkmk", id="community"),
        pytest.param("ultimate", "checkmk", id="ultimate"),
        pytest.param("pro", "pro", id="pro"),
        pytest.param("ultimatemt", "ultimatemt", id="ultimatemt"),
    ],
)
def test_container_namespace_per_edition(script: ModuleType, edition: str, expected: str) -> None:
    assert script.get_container_namespace(edition) == expected


def test_unknown_edition_has_no_namespace(script: ModuleType) -> None:
    with pytest.raises(RuntimeError, match="Unknown edition"):
        script.get_container_namespace("saas")


@pytest.mark.parametrize(
    "version, suffix, expected",
    [
        pytest.param("2.3.0p45", "latest", "2.3.0-latest", id="patch release"),
        pytest.param("2.3.0-2023.12.31", "daily", "2.3.0-daily", id="daily"),
    ],
)
def test_branch_specific_tag_keeps_only_the_base_version(
    script: ModuleType, version: str, suffix: str, expected: str
) -> None:
    assert script.get_branch_specific_tag(version, suffix) == expected


def test_images_are_resolved_per_edition_with_their_registry(script: ModuleType) -> None:
    registry = _FakeRegistry(["community", "ultimate", "pro", "ultimatemt"], [], {})

    resolved = list(
        script.get_docker_image_and_registry("2.3.0p24", ["pro", "community"], [registry])
    )

    assert resolved == [
        (DockerImage("pro/check-mk-pro", "2.3.0p24"), "pro", registry),
        (DockerImage("checkmk/check-mk-community", "2.3.0p24"), "community", registry),
    ]


def test_missing_image_is_not_deleted(
    script: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = _FakeRegistry(["pro"], existing=[], tags={})

    script.delete_image_from_registry(
        DockerImage("pro/check-mk-pro", "2.3.0p24"), "pro", registry, dry_run=False
    )

    assert registry.deleted == []
    assert "does not exist" in capsys.readouterr().out


def test_plain_release_image_is_deleted(script: ModuleType) -> None:
    registry = _FakeRegistry(
        ["pro"],
        existing=["pro/check-mk-pro:2.3.0p24"],
        tags={"pro/check-mk-pro:2.3.0p24": ["pro/check-mk-pro:2.3.0p24"]},
    )

    script.delete_image_from_registry(
        DockerImage("pro/check-mk-pro", "2.3.0p24"), "pro", registry, dry_run=False
    )

    assert registry.deleted == ["pro/check-mk-pro:2.3.0p24"]
    assert registry.moved_tags == []


def test_branch_latest_tag_is_moved_to_previous_release_before_deletion(
    script: ModuleType,
) -> None:
    registry = _FakeRegistry(
        ["pro"],
        existing=["pro/check-mk-pro:2.3.0p24"],
        tags={
            "pro/check-mk-pro:2.3.0p24": [
                "pro/check-mk-pro:2.3.0p24",
                "pro/check-mk-pro:2.3.0-latest",
            ]
        },
        previous_release="2.3.0p23",
    )

    script.delete_image_from_registry(
        DockerImage("pro/check-mk-pro", "2.3.0p24"), "pro", registry, dry_run=False
    )

    assert registry.moved_tags == [("pro/check-mk-pro:2.3.0p23", "2.3.0-latest")]
    assert registry.deleted == ["pro/check-mk-pro:2.3.0p24"]


def test_plain_latest_tag_is_moved_along_with_branch_latest(script: ModuleType) -> None:
    registry = _FakeRegistry(
        ["pro"],
        existing=["pro/check-mk-pro:2.3.0p24"],
        tags={
            "pro/check-mk-pro:2.3.0p24": [
                "pro/check-mk-pro:2.3.0p24",
                "pro/check-mk-pro:2.3.0-latest",
                "pro/check-mk-pro:latest",
            ]
        },
        previous_release="2.3.0p23",
    )

    script.delete_image_from_registry(
        DockerImage("pro/check-mk-pro", "2.3.0p24"), "pro", registry, dry_run=False
    )

    assert registry.moved_tags == [
        ("pro/check-mk-pro:2.3.0p23", "2.3.0-latest"),
        ("pro/check-mk-pro:2.3.0p23", "latest"),
    ]


def test_branch_daily_tag_is_moved_to_previous_daily(script: ModuleType) -> None:
    registry = _FakeRegistry(
        ["pro"],
        existing=["pro/check-mk-pro:2.3.0-2024.03.01"],
        tags={
            "pro/check-mk-pro:2.3.0-2024.03.01": [
                "pro/check-mk-pro:2.3.0-2024.03.01",
                "pro/check-mk-pro:2.3.0-daily",
            ]
        },
        previous_release="2.3.0-2024.02.29",
    )

    script.delete_image_from_registry(
        DockerImage("pro/check-mk-pro", "2.3.0-2024.03.01"), "pro", registry, dry_run=False
    )

    assert registry.moved_tags == [("pro/check-mk-pro:2.3.0-2024.02.29", "2.3.0-daily")]
    assert registry.deleted == ["pro/check-mk-pro:2.3.0-2024.03.01"]


def test_dry_run_changes_nothing(script: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    registry = _FakeRegistry(
        ["pro"],
        existing=["pro/check-mk-pro:2.3.0p24"],
        tags={
            "pro/check-mk-pro:2.3.0p24": [
                "pro/check-mk-pro:2.3.0p24",
                "pro/check-mk-pro:2.3.0-latest",
            ]
        },
    )

    script.delete_image_from_registry(
        DockerImage("pro/check-mk-pro", "2.3.0p24"), "pro", registry, dry_run=True
    )

    assert registry.moved_tags == []
    assert registry.deleted == []
    out = capsys.readouterr().out
    assert "Will be moving '2.3.0-latest' to point to 'pro/check-mk-pro:2.3.0p23'" in out
    assert "Would be deleting image pro/check-mk-pro:2.3.0p24" in out
