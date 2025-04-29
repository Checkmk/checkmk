#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import sys
from argparse import ArgumentParser, BooleanOptionalAction
from argparse import Namespace as Args
from collections.abc import Iterator
from pathlib import Path

import requests

sys.path.insert(0, Path(__file__).parent.parent.parent.as_posix())
from tests.testlib.package_manager import ABCPackageManager, code_name

from cmk.ccc.version import Edition, Version

from buildscripts.scripts.lib.common import flatten, load_editions_file
from buildscripts.scripts.lib.registry import (
    Credentials,
    DockerImage,
    edition_to_registry,
    get_credentials,
    get_default_registries,
    Registry,
)


def hash_file(artifact_name: str) -> str:
    return f"{artifact_name}.hash"


def build_source_artifacts(args: Args, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        file_name = (
            f"check-mk-{edition}-{args.version}.{Edition.from_long_edition(edition).short}.tar.gz"
        )
        internal_only = edition in loaded_yaml["internal_editions"]
        yield file_name, internal_only
        yield hash_file(file_name), internal_only


def build_docker_artifacts(args: Args, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        file_name = f"check-mk-{edition}-docker-{args.version}.tar.gz"
        internal_only = edition in loaded_yaml["internal_editions"]
        yield file_name, internal_only
        yield hash_file(file_name), internal_only


def build_docker_image_name_and_registry(
    args: Args, loaded_yaml: dict, registries: list[Registry]
) -> Iterator[tuple[DockerImage, str, Registry]]:
    def build_folder(ed: str) -> str:
        # TODO: Merge with build-cmk-container.py
        match ed:
            case "raw" | "cloud" | "managed":
                return "checkmk/"
            case "enterprise":
                return f"{ed}/"
            case "saas":
                return ""
            case _:
                raise RuntimeError(f"Unknown edition {ed}")

    for edition in loaded_yaml["editions"]:
        registry = edition_to_registry(edition, registries)
        yield (
            DockerImage(tag=args.version, image_name=f"{build_folder(edition)}check-mk-{edition}"),
            edition,
            registry,
        )


def build_package_artifacts(args: Args, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        for distro in flatten(loaded_yaml["editions"][edition][args.use_case]):
            package_name = ABCPackageManager.factory(code_name(distro)).package_name(
                Edition.from_long_edition(edition), version=args.version
            )
            internal_only = (
                distro in loaded_yaml.get("internal_distros", [])
                or edition in loaded_yaml["internal_editions"]
            )
            yield package_name, internal_only
            yield hash_file(package_name), internal_only


def bom_file_name(edition: str, version: str) -> str:
    return f"check-mk-{edition}-{version}-bill-of-materials.json"


def build_bom_artifacts(args: Args, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        file_name = bom_file_name(edition, args.version)
        internal_only = edition in loaded_yaml.get("internal_editions", [])
        yield file_name, internal_only
        yield hash_file(file_name), internal_only


def build_bom_latest_mapping(args: Args, loaded_yaml: dict) -> dict[str, str]:
    base_version = Version.from_str(args.version).base
    return {
        bom_file_name(
            edition, f"{'' if args.version_agnostic else f'{base_version}-'}latest"
        ): bom_file_name(edition, args.version)
        for edition in loaded_yaml["editions"]
        if edition not in loaded_yaml.get("internal_editions", [])
    }


def file_exists_on_download_server(filename: str, version: str, credentials: Credentials) -> bool:
    url = f"https://download.checkmk.com/checkmk/{version}/{filename}"
    sys.stdout.write(f"Checking for {url}...")
    if (
        requests.head(
            f"https://download.checkmk.com/checkmk/{version}/{filename}",
            auth=(credentials.username, credentials.password),
            timeout=10,
        ).status_code
        != 200
    ):
        sys.stdout.write(" MISSING\n")
        return False
    sys.stdout.write(" AVAILABLE\n")
    return True


def assert_presence_on_download_server(
    args: Args, internal_only: bool, artifact_name: str, credentials: Credentials
) -> None:
    if (
        not file_exists_on_download_server(artifact_name, args.version, credentials)
        != internal_only
    ):
        raise RuntimeError(
            f"{artifact_name} should {'not' if internal_only else ''} "
            "be available on download server!"
        )


def assert_build_artifacts(args: Args, loaded_yaml: dict) -> None:
    credentials = get_credentials()
    registries = get_default_registries()

    for artifact_name, internal_only in build_source_artifacts(args, loaded_yaml):
        assert_presence_on_download_server(args, internal_only, artifact_name, credentials)

    for artifact_name, internal_only in build_package_artifacts(args, loaded_yaml):
        assert_presence_on_download_server(args, internal_only, artifact_name, credentials)

    for artifact_name, internal_only in build_bom_artifacts(args, loaded_yaml):
        assert_presence_on_download_server(args, internal_only, artifact_name, credentials)

    for artifact_name, internal_only in build_docker_artifacts(args, loaded_yaml):
        assert_presence_on_download_server(args, internal_only, artifact_name, credentials)

    for image_name, edition, registry in build_docker_image_name_and_registry(
        args, loaded_yaml, registries
    ):
        if not registry.image_exists(image_name, edition):
            raise RuntimeError(f"{image_name} not found!")

    # cloud images
    # TODO


def dump_bom_artifact_mapping(args: Args, loaded_yaml: dict) -> None:
    print(json.dumps(build_bom_latest_mapping(args, loaded_yaml)))


def parse_arguments() -> Args:
    parser = ArgumentParser()

    parser.add_argument("--editions_file", required=True)

    subparsers = parser.add_subparsers(required=True, dest="command")

    sub_assert_build_artifacts = subparsers.add_parser("assert_build_artifacts")
    sub_assert_build_artifacts.set_defaults(func=assert_build_artifacts)
    sub_assert_build_artifacts.add_argument("--version", required=True, default=False)
    sub_assert_build_artifacts.add_argument("--use_case", required=False, default="release")

    sub_print_bom_artifacts = subparsers.add_parser("dump_bom_artifact_mapping")
    sub_print_bom_artifacts.set_defaults(func=dump_bom_artifact_mapping)
    sub_print_bom_artifacts.add_argument("--version", required=True, default=False)
    sub_print_bom_artifacts.add_argument("--version_agnostic", action=BooleanOptionalAction)

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    args.func(args, load_editions_file(args.editions_file))


if __name__ == "__main__":
    main()
