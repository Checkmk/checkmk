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
from typing import Iterator, NewType, Union

import docker  # type: ignore

VersionRcStripped = NewType("VersionRcStripped", str)


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

    parser.add_argument(
        "--branch",
        required=True,
        help="Branch to build with, e.g. '2.1.0', 'master', 'sandbox-user.name-lower-chars'",
    )
    parser.add_argument(
        "--edition",
        required=True,
        choices=["raw", "enterprise", "managed", "cloud", "saas"],
        help="Checkmk edition to build",
    )
    parser.add_argument("--version", required=True, help="Version to build e.g. '2023.10.19'")
    parser.add_argument(
        "--source_path", required=True, help="Full path to downloaded tar.gz and deb files"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["build", "load", "push", "check_local"],
        help="Action to perform",
    )
    parser.add_argument(
        "--version_rc_aware",
        required=parser.parse_known_args()[0].action in ["load", "check_local"],
        help="RC aware version to load or check e.g. '2.2.0p16-rc3'",
    )

    parser.add_argument(
        "--set_latest_tag",
        type=strtobool,
        nargs="?",
        const=True,
        default=False,
        help="Flag to set/push 'latest' tag to build image",
    )
    parser.add_argument(
        "--set_branch_latest_tag",
        type=strtobool,
        nargs="?",
        const=True,
        default=False,
        help="Flag to set/push 'BRANCHNAME-latest' tag to build image",
    )
    parser.add_argument(
        "--no_cache",
        type=strtobool,
        nargs="?",
        const=True,
        default=False,
        help="Flag to build image without docker cache",
    )
    parser.add_argument(
        "--image_cmk_base", help="Custom CMK base image, defaults to checked in IMAGE_CMK_BASE"
    )

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
    this_repository = f"{registry}{folder}/check-mk-{args.edition}"

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

    LOG.debug(f"placing new tag, repo: {this_repository}, tag: {target_version}")
    image.tag(
        repository=this_repository,
        tag=target_version,
    )
    LOG.debug("Done")

    if args.set_branch_latest_tag:
        LOG.info(f"Create '{args.branch}-latest' tag ...")
        LOG.debug(f"placing new tag, repo: {this_repository}, tag: {args.branch}-latest")
        image.tag(
            repository=this_repository,
            tag=f"{args.branch}-latest",
        )
        LOG.debug("Done")
    else:
        LOG.info(f"Create 'daily' tag ...")
        LOG.debug(f"placing new tag, repo: {this_repository}, tag: {args.branch}-daily")
        image.tag(
            repository=this_repository,
            tag=f"{args.branch}-daily",
        )
        LOG.debug("Done")

    if args.set_latest_tag:
        LOG.info(f"Create 'latest' tag ...")

        LOG.debug(f"placing new tag, repo: {this_repository}, tag: latest")
        image.tag(
            repository=this_repository,
            tag="latest",
        )
        LOG.debug("Done")

    image.reload()
    LOG.debug(f"Final image tags: {image.tags}")


def docker_login(registry: str, docker_username: str, docker_passphrase: str) -> None:
    """Log into a registry"""
    LOG.info(f"Login to {registry} ...")
    docker_client.login(registry=registry, username=docker_username, password=docker_passphrase)


def strip_rc_information(version_tag: str) -> VersionRcStripped:
    return VersionRcStripped(re.sub("-rc[0-9]*", "", version_tag))


def docker_push(
    args: argparse.Namespace, version_tag: VersionRcStripped, registry: str, folder: str
) -> None:
    """Push images to a registry"""
    this_repository = f"{registry}{folder}/check-mk-{args.edition}"

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


def docker_load(args: argparse.Namespace, version_tag: str, registry: str, folder: str) -> None:
    """Load image from tar.gz file"""
    tar_name = f"check-mk-{args.edition}-docker-{args.version}.tar.gz"
    this_repository = f"{registry}{folder}/check-mk-{args.edition}"

    with cwd(tmp_path):
        LOG.debug(f"Now at: {os.getcwd()}")
        LOG.debug(f"Loading image '{tar_name}' ...")

        with gzip.open(tar_name, "rb") as tar_ball:
            loaded_image = docker_client.images.load(tar_ball)[0]

    LOG.debug(f"Create '{this_repository}:{version_tag}' tag ...")
    loaded_image.tag(
        repository=this_repository,
        tag=version_tag,
    )


def check_for_local_image(
    args: argparse.Namespace, version_tag: str, registry: str, folder: str
) -> bool:
    """Check whether image is locally available"""
    image_name_with_tag = f"{registry}{folder}/check-mk-{args.edition}:{version_tag}"

    try:
        image = docker_client.images.get(image_name_with_tag)
        LOG.info(f"{image_name_with_tag} locally available")
        return True
    except docker.errors.ImageNotFound:
        LOG.info(f"{image_name_with_tag} not found locally, please pull or load it")
        return False


def build_tar_gz(
    args: argparse.Namespace, version_tag: str, docker_path: str, docker_repo_name: str
) -> None:
    """Build the check-mk-EDITION-docker-VERSION.tar.gz file"""
    if args.image_cmk_base in (None, "", "None", "null"):
        # make it more ugly and less professional if possible, still to good to maintain
        image_cmk_base = run_cmd(
            cmd=[
                f"{Path(__file__).parent.parent}/docker_image_aliases/resolve.py",
                "IMAGE_CMK_BASE",
            ]
        ).stdout.strip()
    else:
        image_cmk_base = args.image_cmk_base

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
            LOG.info(
                f"{version_tag} contains rc information, do a retagging before docker save with {args.version}."
            )

            # image.tag() is required to make image.save() work properly.
            # See docs of image.save(chunk_size=2097152, named=False):
            # If set to True, the first tag in the tags list will be used to identify the image.
            # Alternatively, any element of the tags list can be used as an argument to use that specific tag as the saved identifier.
            image.tag(
                repository=f"{docker_repo_name}/check-mk-{args.edition}",
                tag=f"{args.version}",
            )
            # reload this object from the server and update attrs
            image.reload()
            LOG.debug(f"Image tags after re-tagging: {image.tags}")
            this_tag = f"{docker_repo_name}/check-mk-{args.edition}:{args.version}"
            with gzip.open(tar_name, "wb") as tar_ball:
                # image.save() can only take elements of the tags list of an image
                # as new tags are appended to the list of tags, the "oldest" one would be used if nothing is specified by the named keyword
                for chunk in image.save(named=this_tag):
                    tar_ball.write(chunk)
            LOG.debug(
                f"Remove image {this_tag} now, it will be loaded from tar.gz at a later point again, see CMK-16498"
            )
            docker_client.images.remove(image=this_tag)
        else:
            with gzip.open(tar_name, "wb") as tar_ball:
                for chunk in image.save(named=this_tag):
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
    # the leading "/" is needed to finally create a valid namespace
    # all registry == "" have a different folder and/or all folder == "" have a different registry
    # a full repo name shall not start with "/"
    folder = f"/{args.edition}"  # known as namespace
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

    # remove potential meta data of tag
    version_tag = Path(args.source_path).name.split("+")[0]

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
            # Ensure we never push rc tags to our registries
            version_tag_rc_stripped = strip_rc_information(version_tag)
            if "-rc" in version_tag:
                LOG.info(f"{version_tag} was a release candidate, do a retagging before pushing")
                docker_tag(
                    args=args,
                    version_tag=version_tag,
                    registry=registry,
                    folder=folder,
                    target_version=version_tag_rc_stripped,
                )

            docker_push(
                args=args, registry=registry, folder=folder, version_tag=version_tag_rc_stripped
            )
        case "load":
            if check_for_local_image(
                args=args, registry=registry, folder=folder, version_tag=args.version
            ):
                return
            LOG.info("Image not found locally, trying to download it ...")
            if release_key := os.environ.get("RELEASE_KEY"):
                internal_deploy_port = os.environ.get("INTERNAL_DEPLOY_PORT")
                internal_deploy_dest = os.environ.get("INTERNAL_DEPLOY_DEST")
                file_pattern = f"check-mk-{args.edition}-docker-{args.version}.tar.gz"
                run_cmd(
                    cmd=[
                        "rsync",
                        "--recursive",
                        "--links",
                        "--perms",
                        "--times",
                        "--verbose",
                        "-e",
                        f"ssh -o StrictHostKeyChecking=no -i {release_key} -p {internal_deploy_port}",
                        f"{internal_deploy_dest}/{args.version_rc_aware}/{file_pattern}",
                        f"{tmp_path}/",
                    ]
                )
            else:
                raise SystemExit(
                    "RELEASE_KEY not found in env, required to download image via rsync"
                )
            docker_load(args=args, registry=registry, folder=folder, version_tag=args.version)
        case "check_local":
            if not check_for_local_image(
                args=args, registry=registry, folder=folder, version_tag=args.version
            ):
                raise SystemExit("Image not found locally")
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
