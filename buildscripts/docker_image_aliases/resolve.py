#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Maps a given Docker Image Alias name (e.g. IMAGE_CMK_BASE) to an unambiguous
image ID, defined in correspondingly named folders containing Dockerfiles.
So the mapping is SCM tracked and thus branch specific and reproducible."""

import argparse
import sys
from pathlib import Path
from subprocess import run


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("alias_name")
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


def main() -> None:
    args = parse_arguments()

    alias_name = args.alias_name
    image_id_value = image_id(alias_name)
    repo_tag = extract_repo_tag(alias_name)

    # The following is a workaround for images being deleted on Nexus.
    # It should be replaced with a solution which allows to keep images forever without having
    # to pull them regularly.

    if args.check:
        print(f"Resolved repo tag: {repo_tag}")
        result = run(["docker", "images", "-q", repo_tag], capture_output=True, check=False)
        if not result.stdout.splitlines():
            print("Does not exist locally, might perform image pull as next step ...")
    else:
        print(image_id_value)
        if repo_tag:
            # We need to pull also the tag, otherwise Nexus may delete those images
            run(["docker", "pull", repo_tag], capture_output=True, check=False)


if __name__ == "__main__":
    main()
