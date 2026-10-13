#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: T201  # It's OK for scripts to print()

"""Maps a given Docker Image Alias name (e.g. IMAGE_CMK_BASE) to an unambiguous
image ID, defined in correspondingly named folders containing Dockerfiles.
So the mapping is SCM tracked and thus branch specific and reproducible."""

import argparse
import base64
import json
import netrc
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from subprocess import run

MANIFEST_MEDIA_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)

CONFIG_READ_ERRORS = (OSError, ValueError, KeyError, TypeError)
NETRC_READ_ERRORS = (OSError, netrc.NetrcParseError)
REQUEST_ERRORS = (urllib.error.URLError, OSError)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("alias_name")
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Do not invoke any docker commands, just print the resolved image ID",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the docker image is already locally available and print the resolved repo tag",
    )

    return parser.parse_args()


def image_id(alias_name: str) -> str:
    """Basically returns the generated image id reported by `docker build` on a given
    image alias folder. Matches against output with or without Docker build kit"""
    try:
        with open(Path(__file__).parent / alias_name / "Dockerfile") as dockerfile:
            for line in dockerfile:
                if "FROM" in line:
                    return line.strip().split()[-1]
    except FileNotFoundError:
        pass

    print(
        f"Docker image alias '{alias_name}' could not be resolved:",
        file=sys.stderr,
    )
    print(
        "Make sure the image alias exists, you're correctly logged into the registry"
        " and the image exists on the registry.",
        file=sys.stderr,
    )

    print("INVALID_IMAGE_ID")

    raise SystemExit(1)


def extract_repo_tag(alias_name: str) -> str:
    # Get the nexus repo tag via the meta.yml file. You're asking why not via docker image inspect?
    # It seems that we don't always get the nexus repo tag via the field "RepoTags", so we go this way...
    with open(Path(__file__).parent / alias_name / "meta.yml") as meta_file:
        tag_lines = [line for line in meta_file.readlines() if "tag:" in line]
        repo_tag = tag_lines and tag_lines[0].split()[1]
        if not repo_tag:
            raise SystemExit(f"meta.yml of {alias_name} has no tag line")
        return repo_tag


def split_repo_tag(repo_tag: str) -> tuple[str, str, str]:
    """Split a registry reference into registry, image name and tag"""
    registry, _, remainder = repo_tag.partition("/")
    image, _, tag = remainder.rpartition(":")
    if not (registry and image and tag) or "." not in registry:
        raise ValueError(f"not a registry reference: {repo_tag!r}")
    return registry, image, tag


def credentials_from_environment() -> str | None:
    """Base64 encoded credentials as provided by our Jenkins jobs"""
    user = os.environ.get("NEXUS_USERNAME")
    password = os.environ.get("NEXUS_PASSWORD")
    if not (user and password):
        return None
    return base64.b64encode(f"{user}:{password}".encode()).decode()


def credentials_from_docker_config(registry: str) -> str | None:
    """Base64 encoded credentials for @registry as stored by `docker login`"""
    directories = [Path.home() / ".docker", Path("/kaniko/.docker")]
    if config := os.environ.get("DOCKER_CONFIG"):
        directories.insert(0, Path(config))

    for directory in directories:
        try:
            auth = json.loads((directory / "config.json").read_text())["auths"][registry]["auth"]
        except CONFIG_READ_ERRORS:
            # No config file, unreadable, malformed or just no entry for @registry
            continue
        if auth:
            return str(auth)
    return None


def credentials_from_netrc(registry: str) -> str | None:
    """Base64 encoded credentials for @registry as stored in ~/.netrc"""
    try:
        authenticators = netrc.netrc().authenticators(registry.split(":", maxsplit=1)[0])
    except NETRC_READ_ERRORS:
        return None
    if not authenticators:
        return None
    login, _account, password = authenticators
    return base64.b64encode(f"{login}:{password or ''}".encode()).decode()


def basic_auth(registry: str) -> str | None:
    """Base64 encoded credentials for @registry - whatever source we find them in first"""
    return (
        credentials_from_environment()
        or credentials_from_docker_config(registry)
        or credentials_from_netrc(registry)
    )


def keep_repo_tag_alive(repo_tag: str) -> None:
    """Request the manifest of @repo_tag to reset Nexus' "last downloaded" timer"""
    try:
        registry, image, tag = split_repo_tag(repo_tag)

        request = urllib.request.Request(
            f"https://{registry}/v2/{image}/manifests/{tag}",
            headers={"Accept": ", ".join(MANIFEST_MEDIA_TYPES)},
        )
        if credentials := basic_auth(registry):
            request.add_header("Authorization", f"Basic {credentials}")

        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 # BNS:28af27
            response.read()
    except (ValueError, *REQUEST_ERRORS) as exception:
        # Don't fail a build over the keep alive request, but do be loud about it: if this
        # silently stops working, the pinned digests start disappearing 30 days later.
        print(f"WARNING: could not refresh '{repo_tag}': {exception}", file=sys.stderr)


def main() -> None:
    args = parse_arguments()

    alias_name = args.alias_name
    image_id_value = image_id(alias_name)
    repo_tag = extract_repo_tag(alias_name)

    # Keeping the tag alive below is a workaround for images being deleted on Nexus.
    # It should be replaced with a solution which allows us to keep images forever without
    # having to touch them regularly.

    if args.check:
        print(f"Resolved repo tag: {repo_tag}")
        if not args.no_docker:
            result = run(["docker", "images", "-q", repo_tag], capture_output=True, check=False)
            if not result.stdout.splitlines():
                print("Does not exist locally, might perform image pull as next step ...")
    else:
        print(image_id_value)
        if repo_tag:
            # We need to touch the tag as well, otherwise Nexus deletes those images
            if args.no_docker:
                keep_repo_tag_alive(repo_tag)
            else:
                run(["docker", "pull", repo_tag], capture_output=True, check=False)


if __name__ == "__main__":
    main()
