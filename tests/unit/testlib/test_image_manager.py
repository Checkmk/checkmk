#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for :mod:`tests.testlib.image_manager`.

Cover the four-step lookup priority of :py:meth:`ABCImageManager.get`:
    a. registry-form tag found locally
    b. bare ``<image>:<version>`` tag found locally (user override)
    c. successful pull from the registry
    d. fallback to building from source

The Docker client and its ``images`` collection are mocked so the tests don't
touch a real Docker daemon.
"""

from typing import Any
from unittest.mock import MagicMock

import docker.errors
import pytest

from tests.testlib.image_manager import ABCImageManager

_REGISTRY_REF = "registry.example/test-image:1.0"
_LOCAL_TAG = "test-image:1.0"
_BUILD_TAG = "test-image:built"


class _FakeImageManager(ABCImageManager):
    """Test double exposing build invocation count and configurable build outcome."""

    def __init__(
        self,
        client: Any,
        *,
        present: set[str] | None = None,
        build_makes_tag_present: bool = True,
    ) -> None:
        super().__init__(client)
        # Mutable: tests/build can grow this set; ``client.images.get`` consults
        # the *same* set, so build()-time mutations are visible to the closure.
        self.present: set[str] = present if present is not None else set()
        self.build_calls = 0
        self._build_makes_tag_present = build_makes_tag_present

    def local_tag(self, version: str) -> str:
        return _LOCAL_TAG

    def registry_ref(self, version: str) -> str:
        return _REGISTRY_REF

    def build(self, version: str) -> str:
        self.build_calls += 1
        if self._build_makes_tag_present:
            self.present.add(_BUILD_TAG)
        return _BUILD_TAG


@pytest.fixture(name="client")
def _client_fx() -> tuple[MagicMock, set[str]]:
    """Return a mocked Docker client wired to a mutable ``present`` set."""
    present: set[str] = set()
    client = MagicMock(name="DockerClient")

    def _get(tag: str) -> MagicMock:
        if tag in present:
            return MagicMock(name=f"image:{tag}")
        raise docker.errors.ImageNotFound(f"no such image: {tag}")

    client.images.get.side_effect = _get
    return client, present


def test_get_returns_registry_tag_when_already_local(
    client: tuple[MagicMock, set[str]],
) -> None:
    """Step (a): the registry-form tag is preferred when present locally."""
    docker_client, present = client
    present.update({_REGISTRY_REF, _LOCAL_TAG})
    manager = _FakeImageManager(docker_client, present=present)

    assert manager.get("1.0") == _REGISTRY_REF
    docker_client.images.pull.assert_not_called()
    assert manager.build_calls == 0


def test_get_returns_local_override_when_registry_missing(
    client: tuple[MagicMock, set[str]],
) -> None:
    """Step (b): falls back to the bare ``<image>:<version>`` tag if user pre-tagged it."""
    docker_client, present = client
    present.add(_LOCAL_TAG)
    manager = _FakeImageManager(docker_client, present=present)

    assert manager.get("1.0") == _LOCAL_TAG
    docker_client.images.pull.assert_not_called()
    assert manager.build_calls == 0


def test_get_pulls_from_registry_when_no_local_tag_present(
    client: tuple[MagicMock, set[str]],
) -> None:
    """Step (c): with nothing local, the manager pulls and returns the registry ref."""
    docker_client, present = client
    manager = _FakeImageManager(docker_client, present=present)

    assert manager.get("1.0") == _REGISTRY_REF
    docker_client.images.pull.assert_called_once_with(_REGISTRY_REF)
    assert manager.build_calls == 0


def test_get_builds_when_registry_pull_returns_not_found(
    client: tuple[MagicMock, set[str]],
) -> None:
    """Step (d) trigger 1: registry says the tag does not exist."""
    docker_client, present = client
    docker_client.images.pull.side_effect = docker.errors.NotFound("missing")
    manager = _FakeImageManager(docker_client, present=present)

    assert manager.get("1.0") == _BUILD_TAG
    assert manager.build_calls == 1


def test_get_builds_when_registry_pull_returns_api_error(
    client: tuple[MagicMock, set[str]],
) -> None:
    """Step (d) trigger 2: registry returns 401/403/etc — treated as a miss, not a hard fail."""
    docker_client, present = client
    docker_client.images.pull.side_effect = docker.errors.APIError("auth failed")
    manager = _FakeImageManager(docker_client, present=present)

    assert manager.get("1.0") == _BUILD_TAG
    assert manager.build_calls == 1


def test_get_raises_when_build_does_not_produce_expected_tag(
    client: tuple[MagicMock, set[str]],
) -> None:
    """If the build returns a tag the daemon doesn't have, ``get`` raises so the failure is loud."""
    docker_client, present = client
    docker_client.images.pull.side_effect = docker.errors.NotFound("missing")
    manager = _FakeImageManager(docker_client, present=present, build_makes_tag_present=False)

    with pytest.raises(RuntimeError, match="did not produce expected tag"):
        manager.get("1.0")
    assert manager.build_calls == 1


def test_lookup_order_pull_skipped_when_override_present(
    client: tuple[MagicMock, set[str]],
) -> None:
    """Manager must not hit the network if step (b) already satisfies the request."""
    docker_client, present = client
    present.add(_LOCAL_TAG)
    manager = _FakeImageManager(docker_client, present=present)

    manager.get("1.0")

    docker_client.images.pull.assert_not_called()
