#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import sys
import urllib.parse
from argparse import Namespace as Args
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import docker  # type: ignore
import requests
import yaml

sys.path.insert(0, Path(__file__).parent.parent.parent.as_posix())

from tests.testlib.utils import get_cmk_download_credentials_file
from tests.testlib.version import ABCPackageManager, code_name

from cmk.utils.version import Edition


class DockerCredentials(NamedTuple):
    username: str
    password: str


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
        url = f"{self.url}/v2/{edition}/check-mk-{edition}/tags/list"
        sys.stdout.write(f"Test if {image.tag} can be found in {url}...")
        exists = (
            image.tag
            in requests.get(
                f"{self.url}/v2/{edition}/check-mk-{edition}/tags/list",
                auth=(self.credentials.username, self.credentials.password),
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
            case _:
                raise RuntimeError(f"Cannnot match editions to registry: {self.editions}")


def get_credentials() -> Credentials:
    with open(get_cmk_download_credentials_file()) as credentials_file:
        username, password = credentials_file.read().strip().split(":", maxsplit=1)

    return Credentials(username=username, password=password)


def hash_file(artifact_name: str) -> str:
    return f"{artifact_name}.hash"


def edition_to_registry(ed: str, registries: list[Registry]) -> Registry:
    for r in registries:
        if ed in r.editions:
            return r
    raise RuntimeError(f"Cannot determine registry for edition: {ed}!")


def build_source_artifacts(args: Args, loaded_yaml: dict) -> Iterator[str]:
    for edition in loaded_yaml["editions"]:
        file_name = (
            f"check-mk-{edition}-{args.version}.{Edition.from_long_edition(edition).short}.tar.gz"
        )
        yield file_name
        yield hash_file(file_name)


def build_docker_artifacts(args: Args, loaded_yaml: dict) -> Iterator[str]:
    for edition in loaded_yaml["editions"]:
        file_name = f"check-mk-{edition}-docker-{args.version}.tar.gz"
        yield file_name
        yield hash_file(file_name)


def build_docker_image_name_and_registry(
    args: Args, loaded_yaml: dict, registries: list[Registry]
) -> Iterator[tuple[DockerImage, str, Registry]]:
    def build_folder(ed: str) -> str:
        # TODO: Merge with build-cmk-container.py
        match ed:
            case "raw" | "cloud":
                return "checkmk"
            case "enterprise" | "managed":
                return ed
            case _:
                raise RuntimeError(f"Unknown edition {ed}")

    for edition in loaded_yaml["editions"]:
        registry = edition_to_registry(edition, registries)
        yield (
            DockerImage(tag=args.version, image_name=f"{build_folder(edition)}/check-mk-{edition}"),
            edition,
            registry,
        )


def build_package_artifacts(args: Args, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        for distro in flatten(loaded_yaml["editions"][edition]["release"]):
            package_name = ABCPackageManager.factory(code_name(distro)).package_name(
                Edition.from_long_edition(edition), version=args.version
            )
            internal_only = distro in loaded_yaml["internal_distros"]
            yield package_name, internal_only
            yield hash_file(package_name), internal_only


def file_exists_on_download_server(filename: str, version: str, credentials: Credentials) -> bool:
    url = f"https://download.checkmk.com/checkmk/{version}/{filename}"
    sys.stdout.write(f"Checking for {url}...")
    if (
        requests.head(
            f"https://download.checkmk.com/checkmk/{version}/{filename}",
            auth=(credentials.username, credentials.password),
        ).status_code
        != 200
    ):
        sys.stdout.write(" MISSING\n")
        return False
    sys.stdout.write(" AVAILABLE\n")
    return True


def assert_build_artifacts(args: Args, loaded_yaml: dict) -> None:
    credentials = get_credentials()
    registries = [
        Registry(
            editions=["enterprise", "managed"],
        ),
        Registry(
            editions=["raw", "cloud"],
        ),
    ]
    for artifact_name in build_source_artifacts(args, loaded_yaml):
        assert file_exists_on_download_server(
            artifact_name, args.version, credentials
        ), f"{artifact_name} should be available on download server!"

    for artifact_name, internal_only in build_package_artifacts(args, loaded_yaml):
        assert (
            file_exists_on_download_server(artifact_name, args.version, credentials)
            != internal_only
        ), (
            f"{artifact_name} should {'not' if internal_only else ''} "
            f"be available on download server!"
        )

    for artifact_name in build_docker_artifacts(args, loaded_yaml):
        assert file_exists_on_download_server(
            artifact_name, args.version, credentials
        ), f"{artifact_name} should be available on download server!"

    for image_name, edition, registry in build_docker_image_name_and_registry(
        args, loaded_yaml, registries
    ):
        assert registry.image_exists(image_name, edition), f"{image_name} not found!"

    # cloud images
    # TODO


def print_internal_distros(args: Args, loaded_yaml: dict) -> None:
    distros = flatten(loaded_yaml["internal_distros"])
    if args.as_codename:
        if diff := distros - loaded_yaml["distro_to_codename"].keys():
            raise Exception(
                f"{args.editions_file} is missing the distro code for the following distros: "
                f"{diff}. Please add the corresponding distro code."
            )
        distros = [loaded_yaml["distro_to_codename"][d] for d in distros]
    if args.as_rsync_exclude_pattern:
        print("{" + ",".join([f"'*{d}*'" for d in distros]) + "}")
        return

    print(" ".join(sorted(set(distros))))


def distros_for_use_case(edition_distros: dict, edition: str, use_case: str) -> Iterable[str]:
    return sorted(
        set(
            distro
            for _edition, use_cases in edition_distros.items()
            if _edition == edition
            for _use_case, distros in use_cases.items()
            if _use_case == use_case
            for distro in flatten(distros)
        )
    )


def print_distros_for_use_case(args: argparse.Namespace, loaded_yaml: dict) -> None:
    edition_distros = loaded_yaml["editions"]
    edition = args.edition
    use_case = args.use_case
    print(" ".join(distros_for_use_case(edition_distros, edition, use_case)))


def flatten(list_to_flatten: Iterable[Iterable[str] | str]) -> Iterable[str]:
    # This is a workaround the fact that yaml cannot "extend" a predefined node which is a list:
    # https://stackoverflow.com/questions/19502522/extend-an-array-in-yaml
    return [h for elem in list_to_flatten for h in ([elem] if isinstance(elem, str) else elem)]


def test_distro_lists():
    with open(Path(__file__).parent.parent.parent / "editions.yml") as editions_file:
        edition_distros = yaml.load(editions_file, Loader=yaml.FullLoader)["editions"]
    # fmt: off
    assert distros_for_use_case(edition_distros, "enterprise", "release") == [
        "almalinux-9", "centos-8",
        "cma-3", "cma-4",
        "debian-10", "debian-11", "debian-12",
        "sles-12sp5", "sles-15sp3", "sles-15sp4", "sles-15sp5",
        "ubuntu-20.04", "ubuntu-22.04",
    ]
    assert distros_for_use_case(edition_distros, "enterprise", "daily") == [
        "almalinux-9", "centos-8",
        "cma-4",
        "debian-12",
        "sles-15sp5",
        "ubuntu-20.04", "ubuntu-22.04", "ubuntu-23.10",
    ]
    # fmt: on


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser()

    parser.add_argument("--editions_file", required=True)

    subparsers = parser.add_subparsers(required=True, dest="command")

    use_cases = subparsers.add_parser("use_cases", help="a help")
    use_cases.set_defaults(func=print_distros_for_use_case)
    use_cases.add_argument("--edition", required=True)
    use_cases.add_argument("--use_case", required=True)

    internal_distros = subparsers.add_parser("internal_distros")
    internal_distros.set_defaults(func=print_internal_distros)
    internal_distros.add_argument("--as-codename", default=False, action="store_true")
    internal_distros.add_argument("--as-rsync-exclude-pattern", default=False, action="store_true")

    sub_assert_build_artifacts = subparsers.add_parser("assert_build_artifacts")
    sub_assert_build_artifacts.set_defaults(func=assert_build_artifacts)
    sub_assert_build_artifacts.add_argument("--version", required=True, default=False)

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    with open(args.editions_file) as editions_file:
        args.func(args, yaml.load(editions_file, Loader=yaml.FullLoader))


if __name__ == "__main__":
    main()
