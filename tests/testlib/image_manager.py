#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resolve Docker images required by tests, preserving origin in the tag.

Lookup order for a given version ``X`` (see :py:meth:`ABCImageManager.get`):

    a. ``<registry>/<image>:X``  — already pulled previously (registry-form tag)
    b. ``<image>:X``             — explicit user override (manual ``docker tag``)
    c. pull ``<registry>/<image>:X`` from the registry
    d. build via Bazel; the rule loads under ``<image>:latest``

Each step returns its own tag form unchanged — no retagging — so ``docker images``
keeps the provenance visible.

Mirrors :mod:`tests.testlib.package_manager`: the abstract class encodes the
orchestration in :py:meth:`ABCImageManager.get`; concrete subclasses declare
only the image-specific bits.
"""

import abc
import logging
import subprocess
from typing import Final

import docker
import docker.errors

from tests.testlib.common.repo import repo_path
from tests.testlib.version import CMKEdition

logger = logging.getLogger(__name__)


class ABCImageManager(abc.ABC):
    """Abstract base for resolving a versioned Docker image.

    Subclasses declare:
      * the bare local tag form (``<image>:<version>``) — for the user override
      * the fully-qualified registry reference — for the pull and the post-pull tag
      * how to build the image from source — including which tag the build produces

    The :py:meth:`get` method orchestrates the lookup priority and returns a
    local tag callers can pass to :py:meth:`docker.client.containers.run`.
    """

    def __init__(self, client: docker.DockerClient) -> None:
        self._client = client

    def get(self, version: str) -> str:
        """Return a local Docker tag for *version*, resolving in priority order."""
        registry_ref = self.registry_ref(version)
        if self._exists_locally(registry_ref):
            logger.info("Image found locally (registry-form): %s", registry_ref)
            return registry_ref

        local_tag = self.local_tag(version)
        if self._exists_locally(local_tag):
            logger.info("Image found locally (override): %s", local_tag)
            return local_tag

        logger.info("Pulling image from registry: %s", registry_ref)
        if self._pull(registry_ref):
            return registry_ref

        logger.info("Image not in registry; building from source for version=%s", version)
        built_tag = self.build(version)
        if not self._exists_locally(built_tag):
            raise RuntimeError(
                f"Build of {self.__class__.__name__} did not produce expected tag {built_tag!r}"
            )
        return built_tag

    def _exists_locally(self, tag: str) -> bool:
        try:
            self._client.images.get(tag)
            return True
        except docker.errors.ImageNotFound:
            return False

    def _pull(self, registry_ref: str) -> bool:
        """Pull *registry_ref*. Returns False if the image isn't in the registry."""
        try:
            self._client.images.pull(registry_ref)
            return True
        except docker.errors.NotFound:
            return False
        except docker.errors.APIError as exc:
            # Some registries return 401/403 for unknown images; treat as miss.
            logger.warning("Pull of %s failed: %s", registry_ref, exc)
            return False

    @abc.abstractmethod
    def local_tag(self, version: str) -> str:
        """Bare ``<image>:<version>`` tag — used as the explicit user-override form."""
        raise NotImplementedError

    @abc.abstractmethod
    def registry_ref(self, version: str) -> str:
        """Fully-qualified ``<registry>/<image>:<version>`` reference."""
        raise NotImplementedError

    @abc.abstractmethod
    def build(self, version: str) -> str:
        """Build the image from source and return the local tag the build produced."""
        raise NotImplementedError


class RelayImageManager(ABCImageManager):
    """Resolves the ``check-mk-relay`` image for a given Checkmk version."""

    REGISTRY: Final = "artifacts.lan.tribe29.com:4000"
    IMAGE_NAME: Final = "check-mk-relay"
    BAZEL_TARGET: Final = "//omd/non-free/relay:image_docker"
    # The bazel rule always loads under this tag (see omd/non-free/relay/BUILD).
    _BAZEL_OUTPUT_TAG: Final = "check-mk-relay:latest"

    def local_tag(self, version: str) -> str:
        return f"{self.IMAGE_NAME}:{version}"

    def registry_ref(self, version: str) -> str:
        return f"{self.REGISTRY}/{self.IMAGE_NAME}:{version}"

    def build(self, version: str) -> str:
        # Remove any stale ``:latest`` so a previous run's image can't shadow this build.
        try:
            self._client.images.remove(self._BAZEL_OUTPUT_TAG, force=True)
            logger.debug("Removed stale %s before rebuild", self._BAZEL_OUTPUT_TAG)
        except docker.errors.ImageNotFound:
            pass
        logger.info("Building relay image via Bazel (version=%s)", version)
        subprocess.run(
            [
                "bazel",
                "run",
                f"--cmk_edition={CMKEdition.ULTIMATE.long}",
                f"--cmk_version={version}",
                self.BAZEL_TARGET,
            ],
            cwd=repo_path(),
            check=True,
        )
        return self._BAZEL_OUTPUT_TAG
