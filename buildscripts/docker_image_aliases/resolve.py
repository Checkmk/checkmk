#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Maps a given Docker Image Alias name (e.g. IMAGE_TESTING) to an unambiguous
image ID, defined in correspondingly named folders containing Dockerfiles.
So the mapping is SCM tracked and thus branch specific and reproducible."""

import re
import sys
from pathlib import Path
from subprocess import run

import yaml


def image_id(alias_name):
    """Basically returns the generated image id reported by `docker build` on a given
    image alias folder. Matches against output with or without Docker build kit"""
    docker_build_result = run(
        ["docker", "build", str(Path(__file__).parent / alias_name)],
        capture_output=True,
        text=True,
        check=False,
    )
    if docker_build_result.returncode == 0:
        for built_image_id in (
            match.groups()[0]
            for output in (docker_build_result.stderr, docker_build_result.stdout)
            for line in output.split("\n")[-10:]
            for pattern in (
                ".*Successfully built ([0-9a-f]+).*",
                ".*writing image sha256:([0-9a-f]+) done.*",
            )
            for match in (re.match(pattern, line),)
            if match
        ):
            return built_image_id[:12]

    print(
        f"Docker image alias '{alias_name}' could not be resolved. `docker build` returned:",
        file=sys.stderr,
    )
    print(f"  command: `{' '.join(docker_build_result.args)}`", file=sys.stderr)
    print(f"  returned: {docker_build_result.returncode}", file=sys.stderr)
    print(f"  stderr: {docker_build_result.stderr}", file=sys.stderr)
    print(f"  stdout: {docker_build_result.stdout}", file=sys.stderr)
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
        repo_tag = yaml.load(meta_file, Loader=yaml.BaseLoader).get("tag")
        if repo_tag:
            # We need to pull also the tag, otherwise Nexus may delete those images
            run(["docker", "pull", repo_tag], capture_output=True, check=False)


if __name__ == "__main__":
    main()
