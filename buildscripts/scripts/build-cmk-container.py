#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Build the CMK container

Usage:

Build .tar.gz file
may require the following env variables
- DOCKER_USERNAME=carl.lama
- DOCKER_PASSPHRASE=eatingHands

scripts/run-uvenv python \
buildscripts/scripts/build-cmk-container.py \
--branch=master \
--edition=enterprise \
--version=2023.10.17 \
--source_path=$PWD/download/2023.10.17 \
--action=build \
-vvvv

(Down)load .tar.gz file
may require the following env variables
- RELEASE_KEY=/path/to/id_rsa
- INTERNAL_DEPLOY_PORT=42
- INTERNAL_DEPLOY_DEST=user@some-domain.tld:/path/

scripts/run-uvenv python \
buildscripts/scripts/build-cmk-container.py \
--branch=2.2.0 \
--edition=enterprise \
--version=2.2.0p16 \
--version_rc_aware=2.2.0p16-rc3 \
--source_path=$PWD/download/2.2.0p16-rc3 \
--action=load \
-vvvv
"""

import argparse
import gzip
import logging
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import NamedTuple

import docker  # type: ignore[import-untyped]

sys.path.insert(0, Path(__file__).parent.parent.parent.as_posix())
from buildscripts.scripts.lib.common import cwd, strtobool


class RegistryConfig(NamedTuple):
    url: str
    namespace: str
    username_env_var: str
    password_env_var: str


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
        help="Branch to build with, e.g. '2.1.0', 'master', 'sandbox-user.name-lower-chars-only'",
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
    cmd: list[str] | str,
    raise_exception: bool = True,
    print_stdout: bool = True,
) -> subprocess.CompletedProcess:
    completed_process = subprocess.run(cmd, encoding="utf-8", capture_output=True, check=False)
    if raise_exception and completed_process.returncode != 0:
        raise Exception(
            f"Failed to execute command '{' '.join(cmd)}' with: {completed_process.stdout}, {completed_process.stderr}"
        )

    if print_stdout:
        LOG.debug(completed_process.stdout.strip())

    return completed_process


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
    LOG.info("Remove temporary directory '%s'", tmp_path)
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

    LOG.info("Creating tag ...")
    LOG.debug("target_version: %s", target_version)
    LOG.debug("args: %s", args)
    LOG.debug("version_tag: %s", version_tag)
    LOG.debug("registry: %s", registry)
    LOG.debug("folder: %s", folder)
    LOG.debug("target_version: %s", target_version)

    LOG.debug("Getting tagged image: %s", source_tag)
    image = docker_client.images.get(source_tag)
    LOG.debug("this image: %s", image)

    LOG.debug("placing new tag, repo: %s, tag: %s", this_repository, target_version)
    image.tag(
        repository=this_repository,
        tag=target_version,
    )
    LOG.debug("Done")

    if args.set_branch_latest_tag:
        LOG.info("Create '%s-latest' tag ...", args.branch)
        LOG.debug("placing new tag, repo: %s, tag: %s-latest", this_repository, args.branch)
        image.tag(
            repository=this_repository,
            tag=f"{args.branch}-latest",
        )
        LOG.debug("Done")
    else:
        LOG.info("Create 'daily' tag ...")
        LOG.debug("placing new tag, repo: %s, tag: %s-daily", this_repository, args.branch)
        image.tag(
            repository=this_repository,
            tag=f"{args.branch}-daily",
        )
        LOG.debug("Done")

    if args.set_latest_tag:
        LOG.info("Create 'latest' tag ...")

        LOG.debug("placing new tag, repo: %s, tag: latest", this_repository)
        image.tag(
            repository=this_repository,
            tag="latest",
        )
        LOG.debug("Done")

    image.reload()
    LOG.debug("Final image tags: %s", image.tags)


def docker_login(registry: str, docker_username: str, docker_passphrase: str) -> None:
    """Log into a registry"""
    LOG.info("Perform docker login to registry '%s' as user '%s' ...", registry, docker_username)
    docker_client.login(registry=registry, username=docker_username, password=docker_passphrase)


def docker_push(
    args: argparse.Namespace,
    version_tag: str,
    registry_config: RegistryConfig,
) -> None:
    """Push images to a registry"""
    this_repository = f"{registry_config.url}{registry_config.namespace}/check-mk-{args.edition}"

    docker_login(
        registry=registry_config.url,
        docker_username=os.environ[registry_config.username_env_var],
        docker_passphrase=os.environ[registry_config.password_env_var],
    )

    if "-rc" in version_tag:
        LOG.info("%s was a release candidate, do a retagging before pushing", version_tag)
        version_tag = re.sub("-rc[0-9]*", "", version_tag)
        docker_tag(
            args=args,
            version_tag=version_tag,
            registry=registry_config.url,
            folder=registry_config.namespace,
            target_version=version_tag,
        )

    LOG.info("Pushing '%s' as '%s' ...", this_repository, version_tag)
    resp = docker_client.images.push(
        repository=this_repository, tag=version_tag, stream=True, decode=True
    )
    for line in resp:
        LOG.debug(line)
        if "error" in line:
            raise ValueError(f"Some error occurred during upload: {line}")

    if args.set_branch_latest_tag:
        LOG.info("Pushing '%s' as '%s-latest' ...", this_repository, args.branch)
        resp = docker_client.images.push(
            repository=this_repository, tag=f"{args.branch}-latest", stream=True, decode=True
        )
    else:
        LOG.info("Pushing '%s' as '%s-daily' ...", this_repository, args.branch)
        resp = docker_client.images.push(
            repository=this_repository, tag=f"{args.branch}-daily", stream=True, decode=True
        )

    for line in resp:
        LOG.debug(line)
        if "error" in line:
            raise ValueError(f"Some error occurred during upload: {line}")

    if args.set_latest_tag:
        LOG.info("Pushing '%s' as 'latest' ...", this_repository)
        resp = docker_client.images.push(
            repository=this_repository, tag="latest", stream=True, decode=True
        )
        for line in resp:
            LOG.debug(line)
            if "error" in line:
                raise ValueError(f"Some error occurred during upload: {line}")


def needed_packages(mk_file: str, output_file: str) -> None:
    """Extract needed packages from MK file"""
    packages = []
    with open(Path(mk_file).resolve()) as file:
        lines = [line.rstrip() for line in file]
        for line in lines:
            this = re.findall(r"^(OS_PACKAGES\s*\+=\s*)(.*?)(?=#|$)", line)
            if len(this):
                packages.append(this[0][-1].strip())

    LOG.debug("Needed packages based on %s: %s", mk_file, packages)
    LOG.debug("Save needed-packages file to '%s'", output_file)
    with open(output_file, "w") as file:
        file.write(" ".join(packages))


def docker_load(args: argparse.Namespace, version_tag: str, registry: str, folder: str) -> None:
    """Load image from tar.gz file"""
    tar_name = f"check-mk-{args.edition}-docker-{args.version}.tar.gz"
    this_repository = f"{registry}{folder}/check-mk-{args.edition}"

    with cwd(tmp_path):
        LOG.debug("Now at: %s", os.getcwd())
        LOG.debug("Loading image '%s' ...", tar_name)

        with gzip.open(tar_name, "rb") as tar_ball:
            loaded_image = docker_client.images.load(tar_ball)[0]

    LOG.debug("Create '%s:%s' tag ...", this_repository, version_tag)
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
        docker_client.images.get(image_name_with_tag)
        LOG.info("%s locally available", image_name_with_tag)
        return True
    except docker.errors.ImageNotFound:
        LOG.info("%s not found locally, please pull or load it", image_name_with_tag)
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
        LOG.debug("Now at: %s", os.getcwd())
        LOG.debug(
            "Building image '%s', tagged: '%s', buildargs: '%s', nocache: '%s' ...",
            docker_path,
            this_tag,
            buildargs,
            args.no_cache,
        )
        image, build_logs = docker_client.images.build(
            # Do not use the cache when set to True
            nocache=args.no_cache,
            buildargs=buildargs,
            tag=this_tag,
            path=docker_path,
        )
        LOG.debug("Built image: %s", image)
        for chunk in build_logs:
            if "stream" in chunk:
                for line in chunk["stream"].splitlines():
                    LOG.debug(line)

        LOG.info("Creating Image-Tarball %s ...", tar_name)
        if "-rc" in version_tag:
            LOG.info(
                "%s contains rc information, do a retagging before docker save with %s.",
                version_tag,
                args.version,
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
            LOG.debug("Image tags after re-tagging: %s", image.tags)
            this_tag = f"{docker_repo_name}/check-mk-{args.edition}:{args.version}"
            with gzip.open(tar_name, "wb") as tar_ball:
                # image.save() can only take elements of the tags list of an image
                # as new tags are appended to the list of tags, the "oldest" one would be used if nothing is specified by the named keyword
                for chunk in image.save(named=this_tag):
                    tar_ball.write(chunk)
            LOG.debug(
                (
                    "Remove image %s now, it will be loaded from tar.gz at a later point again, "
                    "see CMK-16498"
                ),
                this_tag,
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

    LOG.debug("docker_path: %s", docker_path)
    LOG.debug("docker_image_archive: %s", docker_image_archive)
    LOG.debug("pkg_name: %s", pkg_name)
    LOG.debug("architecture: %s", architecture)
    LOG.debug("pkg_file: %s", pkg_file)

    LOG.info("Unpack source tar to %s", tmp_path)
    with tarfile.open(
        name=f"{args.source_path}/check-mk-{args.edition}-{args.version}{suffix}.tar.gz",
        mode="r:gz",
    ) as tar:
        tar.extractall(tmp_path, filter="data")

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

    dockerhub = RegistryConfig(
        url="",  # That's basically dockerhub
        namespace="checkmk",
        username_env_var="DOCKER_USERNAME",
        password_env_var="DOCKER_PASSPHRASE",
    )
    enterprise_registry = RegistryConfig(
        url="registry.checkmk.com",
        namespace="/enterprise",
        username_env_var="DOCKER_USERNAME",
        password_env_var="DOCKER_PASSPHRASE",
    )
    nexus = RegistryConfig(
        url="artifacts.lan.tribe29.com:4000",
        namespace="",
        username_env_var="NEXUS_USERNAME",
        password_env_var="NEXUS_PASSWORD",
    )

    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"][::-1]
    LOG.setLevel(LOG_LEVELS[min(len(LOG_LEVELS) - 1, max(args.verbose, 0))])

    LOG.debug("Docker version: %r", docker_client.info()["ServerVersion"])
    LOG.debug("args: %s", args)

    match args.edition:
        case "raw":
            suffix = ".cre"
            registries = [dockerhub]
        case "enterprise":
            suffix = ".cee"
            registries = [enterprise_registry]
        case "managed":
            suffix = ".cme"
            registries = [dockerhub]
        case "cloud":
            suffix = ".cce"
            registries = [dockerhub, nexus]
        case "saas":
            suffix = ".cse"
            registries = [nexus]
        case _:
            raise Exception(f"ERROR: Unknown edition '{args.edition}'")

    # remove potential meta data of tag
    version_tag = Path(args.source_path).name.split("+")[0]

    LOG.debug("tmp_path: %s", tmp_path)
    LOG.debug("version_tag: %s", version_tag)
    LOG.debug("registry: %s", registries)
    LOG.debug("suffix: %s", suffix)
    LOG.debug("base_path: %s", base_path)

    for registry in registries:
        match args.action:
            case "build":
                build_image(
                    args=args,
                    registry=registry.url,
                    folder=registry.namespace,
                    version_tag=version_tag,
                    suffix=suffix,
                )
            case "push":
                docker_push(
                    args=args,
                    registry_config=registry,
                    version_tag=version_tag,
                )
            case "load":
                if check_for_local_image(
                    args=args,
                    registry=registry.url,
                    folder=registry.namespace,
                    version_tag=args.version,
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
                docker_load(
                    args=args,
                    registry=registry.url,
                    folder=registry.namespace,
                    version_tag=args.version,
                )
            case "check_local":
                if not check_for_local_image(
                    args=args,
                    registry=registry.url,
                    folder=registry.namespace,
                    version_tag=args.version,
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
