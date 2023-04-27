#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Maps a given Docker Image Alias name (e.g. IMAGE_TESTING) to an unambiguous
image ID, defined in correspondingly named folders containing Dockerfiles.
So the mapping is SCM tracked and thus branch specific and reproducible."""

import sys
from pathlib import Path
from subprocess import run


def image_id(alias_name):
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
    print("If IMAGE_TESTING got repinned recently, try a rebase!", file=sys.stderr)

    print("INVALID_IMAGE_ID")

    raise SystemExit(1)


def main():
    """Run resolver, print image ID and pull the associated tag to avoid gc on Nexus"""
    alias_name = sys.argv[1]
    print(image_id(alias_name))

    # The following is a workaround for images being deleted on Nexus.
    # It should be replaced with a solution which allows to keep images forever without having
    # to pull them regularly.

    # Get the nexus repo tag via the meta.yml file. You're asking why not via docker image inspect?
    # It seems that we don't always get the nexus repo tag via the field "RepoTags", so we go this way...
    with open(Path(__file__).parent / alias_name / "meta.yml") as meta_file:
        tag_lines = [line for line in meta_file.readlines() if "tag:" in line]
        repo_tag = tag_lines and tag_lines[0].split()[1]
        if repo_tag:
            # We need to pull also the tag, otherwise Nexus may delete those images
            run(["docker", "pull", repo_tag], capture_output=True, check=False)


if __name__ == "__main__":
    main()
