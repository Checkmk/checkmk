#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Library with container registry focussed functionality
"""

import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import date, timedelta
from os import environ
from pathlib import Path
from typing import NamedTuple, Self, TypeAlias
from urllib.parse import urlparse

import docker  # type: ignore[import-untyped]
import requests

from cmk.ccc.version import BuildDate, ReleaseType, Version

sys.path.insert(0, Path(__file__).parent.parent.parent.parent.as_posix())
from tests.testlib.utils import (
    get_cmk_download_credentials as _get_cmk_download_credentials,
)

# FQIN -> Fully Qualified Image Name
# The format is: registryhost[:port]/repository/imagename[:tag]
FQIN: TypeAlias = str
DockerTag: TypeAlias = str


class Credentials(NamedTuple):
    username: str
    password: str


class DockerImage(NamedTuple):
    image_name: str
    tag: DockerTag

    def full_name(self) -> FQIN:
        return f"{self.image_name}:{self.tag}"

    @classmethod
    def from_str(cls, fqin: FQIN) -> Self:
        image_name, tag = fqin.rsplit(":", 1)
        return cls(image_name, tag)


@dataclass
class Registry:
    editions: Sequence[str]
    url: str = field(init=False)
    credentials: Credentials = field(init=False, repr=False)
    client: docker.DockerClient = field(init=False)
    image_exists: Callable[[DockerImage, str], bool] = field(init=False)
    get_image_tags: Callable[[str], Iterator[DockerTag]] = field(init=False)
    timeout: int | None = None

    def delete_image(self, image: DockerImage) -> None:
        tag = image.tag
        image_name = image.image_name
        headers = {}
        docker_auth = None

        if "hub.docker.com" in self.url:
            # https://stackoverflow.com/questions/44209644/how-do-i-delete-a-docker-image-from-docker-hub-via-command-line
            docker_hub_token = requests.post(
                f"{self.url}/v2/users/login/",
                json={"username": self.credentials.username, "password": self.credentials.password},
                headers={"Content-Type": "application/json"},
                timeout=30,
            ).json()["token"]
            headers = {
                "Content-type": "application/json",
                "Authorization": f"JWT {docker_hub_token}",
            }
            url = f"{self.url}/v2/repositories/{image_name}/tags/{tag}"
        else:
            docker_auth = self.credentials
            # https://wiki.lan.tribe29.com/books/how-to/page/release-withdraw-faq
            url = f"{self.url}/v2/{image_name}/manifests/{tag}"
            headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
            print(f"Get digest of tag '{tag}' from '{url}'")
            response = requests.get(url, auth=docker_auth, headers=headers, timeout=30)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Could not get digest of tag {tag} for image {image_name} with {url}: {response.status_code}"
                )
            digest = response.headers.get("Docker-Content-Digest")
            assert digest, "Did not receive Docker-Content-Digest. Headers: {response.headers}"
            print(f"Digest of tag {tag} of image {image_name}: {digest}")

            url = f"{self.url}/v2/{image_name}/manifests/{digest}"
            # https://registry.checkmk.com/v2/enterprise/check-mk-enterprise/manifests/<DIGEST>

        # German Angst starts here :P
        response = requests.delete(url, auth=docker_auth, headers=headers, timeout=30)

        print(f"Delete result for {image_name}:{tag}: {response.text}")

        if not response.ok:
            raise RuntimeError(
                f"Could not delete image tag {tag} of {image_name} with {url}: {response.status_code}"
            )

    def is_latest_image(self, image: DockerImage) -> bool:
        """
        Check if the given image is also known by a `latest` tag.

        This checks if the image is known as either the `latest` or has a
        version-specific tag (e.g. `1.2.3-latest` or `4.5.6-daily`) applied to it.
        If it is known as a latest version `True` will be returned.
        """
        assert image.tag, f"Expected image to have a tag, it has {image.tag!r}"

        for applied_tag in self.get_all_image_tags(image):
            if applied_tag == "latest":
                sys.stderr.write(f"The image {image.full_name()} is tagged as 'latest'.\n")
                return True

            if applied_tag.endswith(("-latest", "-daily")):
                sys.stderr.write(
                    f"The image {image.full_name()} is a latest of a specific version: {applied_tag}\n"
                )
                return True

        return False

    def get_all_image_tags(self, image: DockerImage) -> tuple[DockerTag]:
        "Get all tags applied to an image"

        image_from_registry = self.client.images.pull(image.image_name, tag=image.tag)
        return tuple(image_from_registry.tags)

    def list_images(self, image_name: str) -> Iterator[DockerImage]:
        print(f"Getting all images for {image_name} on {self.url}")

        for tag in self.get_image_tags(image_name):
            yield DockerImage(image_name, tag)

    def _get_image_tags_docker_hub(self, image: str) -> Iterator[DockerTag]:
        """
        Get image tags for a specific image.

        The image has the format `namespace/image_name`.
        """
        session = requests.Session()
        session.auth = (self.credentials.username, self.credentials.password)

        namespace, image_name = image.split("/")
        # Current max for page_size is 100.
        # We use the maximimum to minimize requests to Dockerhub.
        next_url = (
            f"{self.url}/v2/namespaces/{namespace}/repositories/{image_name}/tags?page_size=100"
        )
        while next_url:
            response = session.get(
                next_url,
                timeout=30,
            )
            if not response.ok:
                sys.stderr.write(f"Request to {next_url} failed: {response.status_code}")
                break

            json_response = response.json()

            for tag in json_response["results"]:
                yield tag["name"]

            next_url = json_response.get("next")

    def _get_image_tags_enterprise(self, image: str) -> Iterator[DockerTag]:
        """
        Get image tags for a specific image.

        The image has the format `namespace/image_name`.
        """
        yield from requests.get(
            f"{self.url}/v2/{image}/tags/list",
            auth=(self.credentials.username, self.credentials.password),
            timeout=30,
        ).json()["tags"]

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

    def image_exists_enterprise(self, image: DockerImage, _edition: str) -> bool:
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
        repository = f"{urlparse(self.url).netloc}/{edition}/check-mk-{edition}"
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

    def get_previous_release_tag(self, image: DockerImage, edition: str) -> str:
        """
        Given an image tag we try to find the tag of the previous release

        This will check for the existance of the tags and only return existing tags.

        Example:
        - 2.3.0p24 -> 2.3.0p23
        - 2.3.0-2024.02.26 -> 2.3.0-2024.02.25
        """

        current_version = Version.from_str(image.tag)
        if current_version.release.is_unspecified():
            raise ValueError(f"{image.tag} misses build information (e.g. p12, 2024.04.03, b4).")

        def create_image(suffix: int | date) -> DockerImage:
            match suffix:
                case int():
                    return DockerImage(
                        image.image_name,
                        f"{current_version}{current_version.release.release_type.name}{suffix}",
                    )
                case date():
                    return DockerImage(
                        image.image_name,
                        f"{current_version}-{suffix.year}.{suffix.month}.{suffix.day}",
                    )

        def decrease_value(tag: int | date) -> int | date:
            match tag:
                case int():
                    return tag - 1
                case date():
                    return tag - timedelta(days=1)

        new_tag_value: int | date

        # Create a new version tag that is lower than the previous one we have.
        # Handling for dates and releases is similar, but with different startin points.
        if current_version.release.release_type == ReleaseType.daily:
            assert isinstance(current_version.release.value, BuildDate)

            initial_release_date = date(
                current_version.release.value.year,
                current_version.release.value.month,
                current_version.release.value.day,
            )
            new_tag_value = decrease_value(initial_release_date)
        else:  # Non-daily patch release
            assert isinstance(current_version.release.value, int)

            new_tag_value = decrease_value(current_version.release.value)

        new_image = create_image(new_tag_value)

        # Limit the amount of attempts to find a replacement tag
        retries = 10
        for _try_number in range(1, retries + 1):
            if self.image_exists(new_image, edition):
                return new_image.tag

            new_tag_value = decrease_value(new_tag_value)
            new_image = create_image(new_tag_value)

        raise RuntimeError(
            f"We have been unable to find an existing previous version for {image.tag} after {retries} attempts. Aborting."
        )

    def tag(self, source: FQIN, new_tag: DockerTag) -> None:
        "Create a tag for `source` with the tag given as `new_tag`"

        if not new_tag.strip():
            raise ValueError(f"Please supply a tag as the target version, not {new_tag.strip()!r}")

        # We want to make sure that we have the path to the registry included,
        # so that we have a proper FQIN.
        registry_addr = urlparse(self.url).netloc
        if registry_addr not in source:
            source = f"{registry_addr}/{source}"

        source_docker_image = DockerImage.from_str(source)

        image = self.client.images.get(source_docker_image.full_name())
        image.tag(
            repository=source_docker_image.image_name,
            tag=new_tag,
        )
        # Reloading is required to have the new tag saved
        image.reload()

        # Push the changes to the registry
        resp = self.client.images.push(
            repository=source_docker_image.image_name,
            tag=new_tag,
            stream=True,
            decode=True,
        )
        for line in resp:
            print(line)

    def __post_init__(self) -> None:
        kwargs = {"timeout": self.timeout} if self.timeout else {}
        self.client = docker.client.from_env(**kwargs)
        self.credentials = get_credentials()
        match self.editions:
            case ["enterprise"]:
                self.url = "https://registry.checkmk.com"
                # Asking why we're also pulling? -> CMK-14567
                self.image_exists = self.image_exists_and_can_be_pulled_enterprise
                self.get_image_tags = self._get_image_tags_enterprise
                self.client.login(
                    registry=self.url,
                    username=self.credentials.username,
                    password=self.credentials.password,
                )
            case ["raw", "cloud", "managed"]:
                self.url = "https://hub.docker.com/"
                self.image_exists = self.image_exists_docker_hub
                self.get_image_tags = self._get_image_tags_docker_hub
            case ["saas"]:
                self.url = "https://artifacts.lan.tribe29.com:4000"
                self.image_exists = self.image_exists_enterprise
                # For nexus, d-intern is not authorized
                self.credentials = Credentials(
                    username=environ["NEXUS_USER"],
                    password=environ["NEXUS_PASSWORD"],
                )
                # According to https://community.sonatype.com/t/api-get-latest-tags-of-all-docker-images/7837/3
                # it looks like we can simply reuse how we talk to our enterprise repo
                self.get_image_tags = self._get_image_tags_enterprise
            case _:
                raise RuntimeError(f"Cannnot match editions to registry: {self.editions}")


def get_credentials() -> Credentials:
    return Credentials(*_get_cmk_download_credentials())


def get_default_registries() -> list[Registry]:
    return [
        Registry(
            editions=["enterprise"],
            timeout=300,  # Our enterprise registry is a bit _slow_, let's give it some more time
        ),
        Registry(
            editions=["raw", "cloud", "managed"],
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
