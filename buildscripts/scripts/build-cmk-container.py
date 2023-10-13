#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Build the CMK container

Usage:
scripts/run-pipenv run python \
buildscripts/scripts/build-cmk-container.py \
--branch=master \
--edition=enterprise \
--version=2023.10.17 \
--source_path=$PWD/download/2023.10.17 \
--action=build \
-vvvv
"""

import argparse
import gzip
import logging
import os
import re
import subprocess
import tarfile
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Iterator, Union

import docker  # type: ignore


def strtobool(val: str | bool) -> bool:
    """Convert a string representation of truth to true (1) or false (0).
    Raises ArgumentTypeError if 'val' is anything else.

    distutils.util.strtobool() no longer part of the standard library in 3.12

    https://github.com/python/cpython/blob/v3.11.2/Lib/distutils/util.py#L308
    """
    if isinstance(val, bool):
        return val
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (for even more output use -vvvv)",
    )

    parser.add_argument("--branch", required=True)
    parser.add_argument(
        "--edition", required=True, choices=["raw", "enterprise", "managed", "cloud", "saas"]
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--source_path", required=True)

    parser.add_argument(
        "--set_latest_tag",
        type=strtobool,
        nargs="?",
        const=True,
        default=False,
    )
    parser.add_argument(
        "--set_branch_latest_tag", type=strtobool, nargs="?", const=True, default=False
    )
    parser.add_argument("--no_cache", type=strtobool, nargs="?", const=True, default=False)
    parser.add_argument("--action", required=True, choices=["build", "push"])

    return parser.parse_args()


def run_cmd(
    cmd: Union[list[str], str],
    shell: bool = False,
    raise_exception: bool = True,
    print_stdout: bool = True,
) -> subprocess.CompletedProcess:
    completed_process = subprocess.run(cmd, encoding="utf-8", capture_output=True, shell=shell)
    if raise_exception and completed_process.returncode != 0:
        raise Exception(
            f"Failed to execute command '{' '.join(cmd)}' with: {completed_process.stdout}, {completed_process.stderr}"
        )

    if print_stdout:
        LOG.debug(completed_process.stdout.strip())

    return completed_process


@contextmanager
def cwd(path: Union[str, Path]) -> Iterator[None]:
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


logging.basicConfig(
    format="[%(asctime)s] [%(levelname)-8s] [%(funcName)-15s:%(lineno)4s] %(message)s",
    level=logging.WARNING,
)
LOG = logging.getLogger(__name__)

base_path = Path.cwd() / "tmp"
base_path.mkdir(parents=True, exist_ok=True)
tmp_path = mkdtemp(dir=base_path, suffix=".cmk-docker")
assert Path(tmp_path).exists()

docker_client = docker.from_env(timeout=1200)


def cleanup() -> None:
    """Cleanup"""
    LOG.info(f"Remove temporary directory '{tmp_path}'")
    rmtree(tmp_path)


def docker_tag(
    args: argparse.Namespace,
    version_tag: str,
    registry: str,
    folder: str,
    target_version: str | None = None,
) -> None:
    """Tag docker image"""
    source_tag = f"checkmk/check-mk-{args.edition}:{version_tag}"
    if target_version is None:
        target_version = version_tag

    LOG.info(f"Creating tag ...")
    LOG.debug(f"target_version: {target_version}")
    LOG.debug(f"args: {args}")
    LOG.debug(f"version_tag: {version_tag}")
    LOG.debug(f"registry: {registry}")
    LOG.debug(f"folder: {folder}")
    LOG.debug(f"target_version: {target_version}")

    LOG.debug(f"Getting tagged image: {source_tag}")
    image = docker_client.images.get(source_tag)
    LOG.debug(f"this image: {image}")

    LOG.debug(
        f"placing new tag: repo: {registry}/{folder}/check-mk-{args.edition}, tag: {target_version}"
    )
    image.tag(
        repository=f"{registry}/{folder}/check-mk-{args.edition}",
        tag=target_version,
    )
    LOG.debug("Done")

    if args.set_branch_latest_tag:
        LOG.info(f"Create '{args.branch}-latest' tag ...")
        LOG.debug(
            f"placing new tag: repo: {registry}/{folder}/check-mk-{args.edition}, tag: {args.branch}-latest"
        )
        image.tag(
            repository=f"{registry}/{folder}/check-mk-{args.edition}",
            tag=f"{args.branch}-latest",
        )
        LOG.debug("Done")
    else:
        LOG.info(f"Create 'daily' tag ...")
        LOG.debug(
            f"placing new tag: repo: {registry}/{folder}/check-mk-{args.edition}, tag: {args.branch}-daily"
        )
        image.tag(
            repository=f"{registry}/{folder}/check-mk-{args.edition}",
            tag=f"{args.branch}-daily",
        )
        LOG.debug("Done")

    if args.set_latest_tag:
        LOG.info(f"Create 'latest' tag ...")

        LOG.debug(
            f"placing new tag: repo: {registry}/{folder}/check-mk-{args.edition}, tag: latest"
        )
        image.tag(
            repository=f"{registry}/{folder}/check-mk-{args.edition}",
            tag="latest",
        )
        LOG.debug("Done")


def docker_login(registry: str, docker_username: str, docker_passphrase: str) -> None:
    """Log into a registry"""
    LOG.info(f"Login to {registry} ...")
    docker_client.login(registry=registry, username=docker_username, password=docker_passphrase)


def docker_push(args: argparse.Namespace, version_tag: str, registry: str, folder: str) -> None:
    """Push images to a registry"""
    this_repository = f"{registry}/{folder}/check-mk-{args.edition}"

    if "-rc" in version_tag:
        LOG.info(f"{version_tag} was a release candidate, do a retagging before pushing")
        version_tag = re.sub("-rc[0-9]*", "", version_tag)
        docker_tag(
            args=args,
            version_tag=version_tag,
            registry=registry,
            folder=folder,
            target_version=version_tag,
        )

    docker_login(
        registry=registry,
        docker_username=os.environ.get("DOCKER_USERNAME", ""),
        docker_passphrase=os.environ.get("DOCKER_PASSPHRASE", ""),
    )

    LOG.info(f"Pushing '{this_repository}' as '{version_tag}' ...")
    resp = docker_client.images.push(
        repository=this_repository, tag=version_tag, stream=True, decode=True
    )
    for line in resp:
        LOG.debug(line)

    if args.set_branch_latest_tag:
        LOG.info(f"Pushing '{this_repository}' as '{args.branch}-latest' ...")
        resp = docker_client.images.push(
            repository=this_repository, tag=f"{args.branch}-latest", stream=True, decode=True
        )
    else:
        LOG.info(f"Pushing '{this_repository}' as '{args.branch}-daily' ...")
        resp = docker_client.images.push(
            repository=this_repository, tag=f"{args.branch}-daily", stream=True, decode=True
        )

    for line in resp:
        LOG.debug(line)

    if args.set_latest_tag:
        LOG.info(f"Pushing '{this_repository}' as 'latest' ...")
        resp = docker_client.images.push(
            repository=this_repository, tag="latest", stream=True, decode=True
        )
        for line in resp:
            LOG.debug(line)


def needed_packages(mk_file: str, output_file: str) -> None:
    """Extract needed packages from MK file"""
    packages = []
    with open(Path(mk_file).resolve(), "r") as file:
        lines = [line.rstrip() for line in file]
        for line in lines:
            this = re.findall(r"^(OS_PACKAGES\s*\+=\s*)(.*?)(?=#|$)", line)
            if len(this):
                packages.append(this[0][-1].strip())

    LOG.debug(f"Needed packages based on {mk_file}: {packages}")
    LOG.debug(f"Save needed-packages file to '{output_file}'")
    with open(output_file, "w") as file:
        file.write(" ".join(packages))


def build_tar_gz(
    args: argparse.Namespace, version_tag: str, docker_path: str, docker_repo_name: str
) -> None:
    """Build the check-mk-EDITION-docker-VERSION.tar.gz file"""
    # make it more ugly and less professional if possible, still to good to maintain
    image_cmk_base = run_cmd(
        cmd=[f"{Path(__file__).parent.parent}/docker_image_aliases/resolve.py", "IMAGE_CMK_BASE"]
    ).stdout.strip()
    buildargs = {
        "CMK_VERSION": args.version,
        "CMK_EDITION": args.edition,
        "IMAGE_CMK_BASE": image_cmk_base,
    }
    this_tag = f"{docker_repo_name}/check-mk-{args.edition}:{version_tag}"
    tar_name = f"check-mk-{args.edition}-docker-{args.version}.tar.gz"

    with cwd(docker_path):
        LOG.debug(f"Now at: {os.getcwd()}")
        LOG.debug(
            f"Building image '{docker_path}', tagged: '{this_tag}', buildargs: '{buildargs}', nocache: '{args.no_cache}' ..."
        )
        image, build_logs = docker_client.images.build(
            # Do not use the cache when set to True
            nocache=args.no_cache,
            buildargs=buildargs,
            tag=this_tag,
            path=docker_path,
        )
        LOG.debug(f"Built image: {image}")
        for chunk in build_logs:
            if "stream" in chunk:
                for line in chunk["stream"].splitlines():
                    LOG.debug(line)

        LOG.info(f"Creating Image-Tarball {tar_name} ...")
        if "-rc" in version_tag:
            LOG.info(f"{version_tag} contains rc information, do a retagging before docker save.")
            image.tag(
                repository=f"{docker_repo_name}/check-mk-{args.edition}",
                tag=f"check-mk-{args.edition}:{args.version}",
            )

            with gzip.open(tar_name, "wb") as tar_ball:
                for chunk in image.save():
                    tar_ball.write(chunk)

            docker_client.remove(image=f"{docker_repo_name}/check-mk-{args.edition}:{args.version}")
        else:
            with gzip.open(tar_name, "wb") as tar_ball:
                for chunk in image.save():
                    tar_ball.write(chunk)


def build_image(
    args: argparse.Namespace,
    registry: str,
    folder: str,
    version_tag: str,
    suffix: str,
    docker_repo_name: str = "checkmk",
) -> None:
    """Build an image, create a tar ball and tag the image"""
    docker_path = f"{tmp_path}/check-mk-{args.edition}-{args.version}{suffix}/docker_image"
    docker_image_archive = f"check-mk-{args.edition}-docker-{args.version}.tar.gz"
    pkg_name = f"check-mk-{args.edition}-{args.version}"
    architecture = run_cmd(cmd=["dpkg", "--print-architecture"]).stdout.strip()
    pkg_file = f"{pkg_name}_0.jammy_{architecture}.deb"

    LOG.debug(f"docker_path: {docker_path}")
    LOG.debug(f"docker_image_archive: {docker_image_archive}")
    LOG.debug(f"pkg_name: {pkg_name}")
    LOG.debug(f"architecture: {architecture}")
    LOG.debug(f"pkg_file: {pkg_file}")

    LOG.info(f"Unpack source tar to {tmp_path}")
    with tarfile.open(
        name=f"{args.source_path}/check-mk-{args.edition}-{args.version}{suffix}.tar.gz",
        mode="r:gz",
    ) as tar:
        tar.extractall(tmp_path)

    LOG.info("Copy debian package ...")
    run_cmd(cmd=["cp", f"{args.source_path}/{pkg_file}", docker_path])

    LOG.info("Building container image ...")
    if version_tag is None:
        raise Exception("Required VERSION_TAG is not set.")
    needed_packages(
        mk_file="omd/distros/UBUNTU_22.04.mk", output_file=f"{docker_path}/needed-packages"
    )

    build_tar_gz(
        args=args,
        version_tag=version_tag,
        docker_path=docker_path,
        docker_repo_name=docker_repo_name,
    )

    LOG.info("Move Image-Tarball ...")
    run_cmd(cmd=["mv", "-v", f"{docker_path}/{docker_image_archive}", args.source_path])

    docker_tag(args=args, version_tag=version_tag, registry=registry, folder=folder)


def main() -> None:
    args: argparse.Namespace = parse_arguments()

    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"][::-1]
    LOG.setLevel(LOG_LEVELS[min(len(LOG_LEVELS) - 1, max(args.verbose, 0))])

    LOG.debug("Docker version: %r", docker_client.info()["ServerVersion"])
    LOG.debug(f"args: {args}")

    # Default to our internal registry, set it to "" if you want push it to dockerhub
    registry = os.environ.get("CHECKMK_REGISTRY", "registry.checkmk.com")
    folder = f"{args.edition}"  # known as namespace
    match args.edition:
        case "raw":
            suffix = ".cre"
            registry = ""
            folder = "checkmk"
        case "enterprise":
            suffix = ".cee"
        case "managed":
            suffix = ".cme"
        case "cloud":
            suffix = ".cce"
            registry = ""
            folder = "checkmk"
        case "saas":
            suffix = ".cse"
            registry = "artifacts.lan.tribe29.com:4000"
            folder = ""
        case _:
            raise Exception(f"ERROR: Unknown edition '{args.edition}'")

    version_tag = Path(args.source_path).name

    LOG.debug(f"tmp_path: {tmp_path}")
    LOG.debug(f"version_tag: {version_tag}")
    LOG.debug(f"registry: {registry}")
    LOG.debug(f"suffix: {suffix}")
    LOG.debug(f"base_path: {base_path}")

    if os.environ.get("NEXUS_USERNAME"):
        docker_login(
            registry=os.environ.get("DOCKER_REGISTRY", ""),
            docker_username=os.environ.get("NEXUS_USERNAME", ""),
            docker_passphrase=os.environ.get("NEXUS_PASSWORD", ""),
        )

    match args.action:
        case "build":
            build_image(
                args=args, registry=registry, folder=folder, version_tag=version_tag, suffix=suffix
            )
        case "push":
            docker_push(args=args, registry=registry, folder=folder, version_tag=version_tag)
        case _:
            raise Exception(
                f"Unknown action: {args.action}, should be prevented by argparse options"
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Feigling")
    except Exception as e:
        raise e
    finally:
        cleanup()
