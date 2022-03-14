#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This script stores a given Docker image in our internal registry and creates a textual
docker image alias (in form of a Dockerfile file containing the provided data and a new sha
based image name) referencing the remotly stored image via unique ID

run

  >> ./register.py IMAGE_DEBIAN_DEFAULT debian:buster-slim

to create an (internally used) Dockerfile inside `IMAGE_DEBIAN_DEFAULT/`:

which can be used like this (Dockerfile example):

  docker build --build-arg "IMAGE_DEBIAN_DEFAULT=$(./resolve.sh IMAGE_DEBIAN_DEFAULT)" -t debian_example example
"""

from typing import List, Dict, Optional
import os
import sys
import json
import yaml
import docker
import shlex
import subprocess
import logging
from pathlib import Path

LOG = logging.getLogger("register-dia")
REGISTRY = "artifacts.lan.tribe29.com:4000"


def split_source_name(raw_source):
    """
    >>> split_source_name("artifacts.lan.tribe29.com:4000/debian:latest")
    ('artifacts.lan.tribe29.com:4000', 'debian', ['latest'])
    >>> split_source_name("debian:buster-slim")
    ('', 'debian', ['buster-slim'])
    >>> split_source_name("debian")
    ('', 'debian', ['latest'])
    >>> split_source_name("artifacts.lan.tribe29.com:4000/hadolint/hadolint")
    ('artifacts.lan.tribe29.com:4000/hadolint', 'hadolint', ['latest'])
    """
    *registry_name, image_name = raw_source.split("/")
    base_name, *tags = image_name.split(":")
    assert len(tags) <= 1
    return "/".join(registry_name), base_name, tags if tags else ["latest"]


def cmd_result(cmd, cwd=None):
    """Run @cmd and return non-empty lines"""
    return [
        line
        for line in subprocess.check_output(
            shlex.split(cmd), cwd=cwd, universal_newlines=True).split("\n")
        if line.strip()
    ]


def commit_id(directory) -> str:
    return cmd_result(f'git rev-parse --short HEAD', cwd=directory)[0]


def cmk_branch(directory) -> str:
    return min(
        ("master", "2.0.0", "1.6.0", "1.5.0"),
        key=lambda b: int(cmd_result(
            f" git rev-list --max-count=1000 --count HEAD...origin/{b}", cwd=directory)[0]))


def git_info():
    cwd = os.path.dirname(__file__)
    a, b = cmk_branch(directory=cwd), commit_id(directory=cwd)
    return [a,b]


def main():
    logging.basicConfig(
        level=logging.DEBUG if "-v" in sys.argv else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s")

    alias_name, source_name = sys.argv[1], sys.argv[2]
    alias_file_name = os.path.join(os.path.dirname(__file__), "docker_image_aliases.txt")

    client = docker.from_env(timeout=1200)
    LOG.info("Docker version: %r", client.info()["ServerVersion"])

    print(f"pull image {source_name}")
    image = client.images.pull(source_name)

    _source_registry, source_base_name, source_tags = split_source_name(source_name)

    name_in_registry = (f"{REGISTRY}/{source_base_name}:"
                        f"{'-'.join(source_tags + ['image-alias'] + git_info())}")

    LOG.info("tag image as %s", name_in_registry)
    result = image.tag(name_in_registry)
    assert result

    print(f"push image as {name_in_registry}")
    push_response = tuple(map(
        json.loads,
        filter(
            lambda x: x.strip(),
            client.images.push(name_in_registry).split("\n"))))

    LOG.debug(push_response)

    assert not any("error" in parsed for parsed in push_response)

    digest = next(parsed for parsed in push_response if "aux" in parsed)["aux"]["Digest"]

    remote_image_name = f"{REGISTRY}/{source_base_name}@{digest}"

    LOG.info("pull sha %s (for verification)", remote_image_name)
    repulled = client.images.pull(remote_image_name)

    new_digests = [d for d in repulled.attrs["RepoDigests"] if d.startswith(REGISTRY)]
    assert remote_image_name in new_digests

    alias_dir = Path(os.path.dirname(__file__)) / alias_name
    alias_dir.mkdir(parents=True)

    print(f"create new alias at {alias_dir.absolute()}")
    with open(alias_dir / "Dockerfile", "w") as dockerfile:
        print(f'FROM {remote_image_name}', file=dockerfile)

    with open(alias_dir / "meta.yml", "w") as metafile:
        yaml.dump({"source": source_name, "tag": name_in_registry}, stream=metafile)

if __name__ == "__main__":
    main()

