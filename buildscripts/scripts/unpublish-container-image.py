#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
from collections.abc import Iterator, Sequence
from typing import Literal

from cmk.ccc.version import Version

from .lib.common import load_editions_file
from .lib.registry import DockerImage, edition_to_registry, get_default_registries, Registry

Edition = Literal["raw", "cloud", "enterprise", "managed"]


def main():
    arguments = parse_arguments()
    editions = list(load_editions_file(arguments.editions_file)["editions"])
    editions = [arguments.edition] if arguments.edition != "all" else editions
    registries = get_default_registries()

    match arguments.action:
        case "list":
            for edition in editions:
                registry = edition_to_registry(edition, registries)

                container_name_and_namespace = (
                    f"{get_container_namespace(edition)}/check-mk-{edition}"
                )
                for image in registry.list_images(container_name_and_namespace):
                    print(image)

        case "delete":
            for image, edition, registry in get_docker_image_and_registry(
                arguments.image_tag, editions, registries
            ):
                delete_image_from_registry(image, edition, registry, arguments.dry_run)
        case _:
            raise RuntimeError("Unexpected action")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete a specific container image from the registries",
        epilog=(
            "Registry credentials will be taken from ~/.cmk-credentials, "
            "they have to be present in form <username>:<password> in there."
        ),
    )
    parser.add_argument("--editions_file", required=True)
    parser.add_argument(
        "--edition",
        default="all",
        help="Specify for what edition to process. Default: all",
        choices=["raw", "cloud", "enterprise", "managed", "all"],
    )

    subparsers = parser.add_subparsers(help="action to perform", required=True)

    # List actions
    list_parser = subparsers.add_parser("list", help="List available images and tags")
    list_parser.set_defaults(action="list")

    # Delete actions
    parser_delete = subparsers.add_parser("delete", help="Delete an image with a specific tag")
    parser_delete.add_argument(
        "--dry-run", action="store_true", help="Perform a run without altering the registries."
    )
    parser_delete.add_argument("--image-tag", required=True, help="The version to delete")
    parser_delete.set_defaults(action="delete")

    return parser.parse_args()


def is_latest(image_tag: str) -> bool:
    assert image_tag, f"Expected to receive image tag, got {image_tag!r}"

    # Has to match branch-specific latest (e.g. "2.3.0-latest") and literal "latest"
    if image_tag.endswith("latest"):
        return True

    return False


def get_docker_image_and_registry(
    version: str, editions: Sequence[Edition], registries: list[Registry]
) -> Iterator[tuple[DockerImage, Edition, Registry]]:
    for edition in editions:
        registry = edition_to_registry(edition, registries)

        yield (
            DockerImage(
                tag=version,
                image_name=f"{get_container_namespace(edition)}/check-mk-{edition}",
            ),
            edition,
            registry,
        )


def get_container_namespace(edition: Edition) -> str:
    match edition:
        case "raw" | "cloud":
            return "checkmk"
        case "enterprise" | "managed":
            return edition
        case _:
            raise RuntimeError(f"Unknown edition {edition}")


def delete_image_from_registry(
    image: DockerImage, edition: Edition, registry: Registry, dry_run: bool
) -> None:
    if not registry.image_exists(image, edition):
        print(f"Image {image.full_name()} does not exist on {registry.url} - ignoring")
        return

    # We do not want to delete any latest ("latest", a version-specific latest like
    # "2.3.0-latest" or 2.3.0-daily), because this would impact different workflows
    # expecting such a version.
    # In such a case we will move the tag to the previous version found on the registry.
    if registry.is_latest_image(image):
        previous_release_tag = registry.get_previous_release_tag(image, edition)
        previous_release_image = DockerImage(image.image_name, tag=previous_release_tag)
        branch_latest_tag = get_branch_specific_tag(previous_release_tag, "latest")

        current_image_tags = registry.get_all_image_tags(image)

        image_is_branch_latest = branch_latest_tag in current_image_tags
        if image_is_branch_latest:
            print(
                f"Will be moving {branch_latest_tag!r} to point to {previous_release_image.full_name()!r}"
            )

            if not dry_run:
                registry.tag(
                    source=previous_release_image.full_name(),
                    new_tag=branch_latest_tag,
                )
        else:
            print(f"Tag {branch_latest_tag!r} does not point to this image, not moving this tag.")

        image_is_latest_latest = "latest" in current_image_tags
        if image_is_latest_latest:
            print(f"Will be moving 'latest' to point to {previous_release_image.full_name()!r}")

            if not dry_run:
                registry.tag(
                    source=previous_release_image.full_name(),
                    new_tag="latest",
                )
        else:
            print("Tag 'latest' does not point to this image, not moving this tag.")

        branch_specific_daily_tag = get_branch_specific_tag(
            previous_release_image.full_name(), "daily"
        )
        image_is_branch_daily = branch_specific_daily_tag in current_image_tags
        if image_is_branch_daily:
            print(
                f"Will be moving {branch_specific_daily_tag!r} to point to {previous_release_image.full_name()!r}"
            )

            if not dry_run:
                registry.tag(
                    source=previous_release_image.full_name(),
                    new_tag=branch_specific_daily_tag,
                )
        else:
            print(
                f"Tag {branch_specific_daily_tag!r} does not point to this image, not moving this tag."
            )

    if dry_run:
        print(f"Would be deleting image {image.full_name()} from {registry.url}")
        return

    # At this point the image with the tag we want to remove should be the only reference to
    # that image. We assume that deleting the tag will also remove the image - removal of
    # the image hash should not be required, because the registry should handle deleting images
    # without tags applied.
    print(f"Deleting image {image.full_name()} from {registry.url}...")
    registry.delete_image(image)
    print(f"Deleted image {image.full_name()} from {registry.url}")


def get_branch_specific_tag(version: str, suffix: str) -> str:
    """
    Get the branch-specific tag with desired suffix

    >>> get_branch_specific_tag("2.3.0p45", "latest")
    '2.3.0-latest'
    >>> get_branch_specific_tag("2.3.0-2023.12.31", "daily")
    '2.3.0-daily'
    """
    version_object = Version.from_str(version)
    return f"{version_object.base}-{suffix}"


if __name__ == "__main__":
    main()
