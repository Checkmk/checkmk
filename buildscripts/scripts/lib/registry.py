#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Library with container registry focussed functionality
"""
import sys
import urllib.parse
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from os import environ
from pathlib import Path
from typing import NamedTuple

import docker  # type: ignore
import requests
import yaml

sys.path.insert(0, Path(__file__).parent.parent.parent.parent.as_posix())
from tests.testlib.utils import get_cmk_download_credentials as _get_cmk_download_credentials


class Credentials(NamedTuple):
    username: str
    password: str


class DockerImage(NamedTuple):
    image_name: str
    tag: str

    def full_name(self) -> str:
        return f"{self.image_name}:{self.tag}"


@dataclass
class Registry:
    editions: Sequence[str]
    url: str = field(init=False)
    credentials: Credentials = field(init=False)
    client: docker.DockerClient = field(init=False)
    image_exists: Callable[[DockerImage, str], bool] = field(init=False)

    def image_exists_docker_hub(self, image: DockerImage, _edition: str) -> bool:
        sys.stdout.write(f"Test if {image.full_name()} is available...")
        with suppress(docker.errors.NotFound):
            self.client.images.get_registry_data(image.full_name())
            sys.stdout.write(" OK\n")
            return True
        return False

    def image_exists_and_can_be_pulled_enterprise(self, image: DockerImage, edition: str) -> bool:
        if not self.image_exists_enterprise(image, edition):
            return False
        return self.image_can_be_pulled_enterprise(image, edition)

    def image_exists_enterprise(self, image: DockerImage, edition: str) -> bool:
        url = f"{self.url}/v2/{image.image_name}/tags/list"
        sys.stdout.write(f"Test if {image.tag} can be found in {url}...")
        exists = (
            image.tag
            in requests.get(
                url,
                auth=(self.credentials.username, self.credentials.password),
                timeout=30,
            ).json()["tags"]
        )
        if not exists:
            sys.stdout.write(" NO!\n")
            return False
        sys.stdout.write(" OK\n")
        return True

    def image_can_be_pulled_enterprise(self, image: DockerImage, edition: str) -> bool:
        repository = f"{urllib.parse.urlparse(self.url).netloc}/{edition}/check-mk-{edition}"
        sys.stdout.write(f"Test if {image.tag} can be pulled from {repository}...")
        # Be sure we don't have the image locally... there is no force pull
        with suppress(docker.errors.ImageNotFound):
            self.client.images.remove(f"{repository}:{image.tag}")
        try:
            self.client.images.pull(
                tag=image.tag,
                repository=repository,
            )
        except docker.errors.APIError as e:
            sys.stdout.write(f" NO! Error was: {e}\n")
            return False
        sys.stdout.write(" OK\n")
        return True

    def __post_init__(self):
        self.client = docker.client.from_env()
        self.credentials = get_credentials()
        match self.editions:
            case ["enterprise", "managed"]:
                self.url = "https://registry.checkmk.com"
                # Asking why we're also pulling? -> CMK-14567
                self.image_exists = self.image_exists_and_can_be_pulled_enterprise
                self.client.login(
                    registry=self.url,
                    username=self.credentials.username,
                    password=self.credentials.password,
                )
            case ["raw", "cloud"]:
                self.url = "https://docker.io"
                self.image_exists = self.image_exists_docker_hub
            case ["saas"]:
                self.url = "https://artifacts.lan.tribe29.com:4000"
                self.image_exists = self.image_exists_enterprise
                # For nexus, d-intern is not authorized
                self.credentials = Credentials(
                    username=environ["NEXUS_USER"],
                    password=environ["NEXUS_PASSWORD"],
                )
            case _:
                raise RuntimeError(f"Cannnot match editions to registry: {self.editions}")


def get_credentials() -> Credentials:
    return Credentials(*_get_cmk_download_credentials())


def get_default_registries() -> list[Registry]:
    return [
        Registry(
            editions=["enterprise", "managed"],
        ),
        Registry(
            editions=["raw", "cloud"],
        ),
        Registry(
            editions=["saas"],
        ),
    ]


def edition_to_registry(edition: str, registries: list[Registry]) -> Registry:
    for registry in registries:
        if edition in registry.editions:
            return registry
    raise RuntimeError(f"Cannot determine registry for edition: {edition}!")
