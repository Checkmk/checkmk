#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import tarfile
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Literal

import docker  # type: ignore[import-untyped]
import dockerpty  # type: ignore[import-untyped]
import requests
from docker.models.images import Image  # type: ignore[import-untyped]
from typing_extensions import TypedDict

from tests.testlib import get_cmk_download_credentials
from tests.testlib.repo import git_commit_id, git_essential_directories, repo_path
from tests.testlib.utils import package_hash_path
from tests.testlib.version import CMKVersion

# Make the tests.testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

_DOCKER_REGISTRY = "artifacts.lan.tribe29.com:4000"
_DOCKER_REGISTRY_URL = "https://%s/v2/" % _DOCKER_REGISTRY
# Increase this to enforce invalidation of all existing images
_DOCKER_BUILD_ID = 1

logger = logging.getLogger()


class DockerBind(TypedDict):
    bind: str
    mode: Literal["ro"]


def execute_tests_in_container(
    distro_name: str,
    docker_tag: str,
    version: CMKVersion,
    result_path: Path,
    command: list[str],
    interactive: bool,
) -> int:
    client: docker.DockerClient = _docker_client()
    info = client.info()
    logger.info("Docker version: %s", info["ServerVersion"])

    image_name_with_tag = _create_cmk_image(client, distro_name, docker_tag, version)

    # Start the container
    container: docker.Container
    with _start(
        client,
        image=image_name_with_tag,
        # TODO: Re-enable using dedicated container names, the following causes name conflicts:
        # name=f"test-{container_name_suffix(distro_name, docker_tag)}",
        command="/bin/bash",
        host_config=client.api.create_host_config(
            # Create some init process that manages signals and processes
            init=True,
            # needed to make the overlay mounts work on the /git directory
            # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
            privileged=True,
            # Important to workaround really high default of docker which results
            # in problems when trying to close all FDs in Python 2.
            ulimits=[
                docker.types.Ulimit(name="nofile", soft=2048, hard=2048),
            ],
            binds=_runtime_binds(),
        ),
        stdin_open=True,
        tty=True,
    ) as container:
        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        _cleanup_previous_virtual_environment(container, version)
        _reuse_persisted_virtual_environment(container, version)

        if interactive:
            logger.info("+-------------------------------------------------")
            logger.info("| Next steps: Start the test of your choice, for example:")
            logger.info("| ")
            logger.info("| make -C tests test-integration")
            logger.info("| ")
            logger.info("|   Execute all integration tests")
            logger.info("| ")
            logger.info("| pytest -T integration tests/integration/livestatus/test_livestatus.py")
            logger.info("| ")
            logger.info("|   Execute some integration tests")
            logger.info("| ")
            logger.info(
                "| pytest -T integration "
                "tests/integration/livestatus/test_livestatus.py "
                "-k test_service_custom_variables "
            )
            logger.info("| ")
            logger.info("|   Execute a single test")
            logger.info("| ")
            logger.info("| !!!WARNING!!!")
            logger.info("| The version of Checkmk you test against is set using the VERSION ")
            logger.info("| environment variable and defaults to the current daily build of ")
            logger.info("| your branch.")
            logger.info("| If you want to test a patched version, you need patch it before ")
            logger.info("| running tests.")
            logger.info("+-------------------------------------------------")

            if command:
                dockerpty.exec_command(
                    client.api,
                    container.id,
                    ["/git/scripts/run-pipenv", "run"] + command,
                )
            dockerpty.exec_command(client.api, container.id, ["/git/scripts/run-pipenv", "shell"])

            return 0

        # Now execute the real test in the container context
        exit_code = _exec_run(
            container,
            command,
            check=False,
            environment=_container_env(version),
            workdir="/git",
            stream=True,
            tty=True,  # NOTE: Some tests require a tty (e.g. test-update)!
        )

        # Collect the test results located in /results of the container. The
        # jenkins job will make it available as artifact later
        _copy_directory(container, Path("/results"), result_path)

        return exit_code


def _docker_client() -> docker.DockerClient:
    return docker.from_env(timeout=1200)


def _get_or_load_image(client: docker.DockerClient, image_name_with_tag: str) -> Image | None:
    try:
        image = client.images.get(image_name_with_tag)
        logger.info("  Available locally (%s)", image.short_id)

        # Verify that this is in sync with remote version
        registry_data = _get_registry_data(client, image_name_with_tag)
        if not registry_data:
            logger.info("  Registry state is unknown, using local image")
            return image

        if registry_data.short_id == image.short_id:
            logger.info("  Is in sync with registry, using local image")
            return image

        logger.info("  Not in sync with registry (%s), trying to pull", registry_data.short_id)
    except docker.errors.ImageNotFound:
        logger.info(
            "  Not available locally, trying to pull (May take some time. Grab a coffee or two...)"
        )

    try:
        image = client.images.pull(image_name_with_tag)
        logger.info("  Downloaded (%s)", image.short_id)
        return image
    except docker.errors.NotFound:
        logger.info("  Not available from registry")
    except docker.errors.APIError as e:
        _handle_api_error(e)

    return None


def _get_registry_data(client: docker.DockerClient, image_name_with_tag: str) -> Image | None:
    try:
        registry_data = client.images.get_registry_data(image_name_with_tag)
        logger.info("  pull '%s'", image_name_with_tag)
        return registry_data.pull()
    except docker.errors.NotFound:
        logger.info("  Not available from registry")
        return None
    except docker.errors.APIError as e:
        _handle_api_error(e)
        return None


def _handle_api_error(e: docker.errors.APIError) -> None:
    if "no basic auth" in "%s" % e:
        raise Exception(
            "No authentication information stored for %s. You will have to login to the "
            'registry using "docker login %s" to be able to execute the tests.'
            % (_DOCKER_REGISTRY, _DOCKER_REGISTRY_URL)
        )
    if "request canceled while waiting for connection" in "%s" % e:
        return None
    if "dial tcp: lookup " in "%s" % e:
        # May happen when offline on ubuntu
        return None
    raise e


def check_for_local_package(version: CMKVersion, distro_name: str) -> bool:
    """Checks package_download folder for a Checkmk package and returns True if
    exactly one package is available and meets some requirements. If there are
    invalid packages, the application terminates."""
    packages_dir = repo_path() / "package_download"
    if available_packages := [
        p for p in packages_dir.glob("*") if re.match("^.*check-mk.*(rpm|deb)$", p.name)
    ]:
        if len(available_packages) > 1:
            logger.error(
                "Error: There must be exactly one Checkmk package in %s, but there are %d:",
                packages_dir,
                len(available_packages),
            )
            for path in available_packages:
                logger.error("Error:   %s", path)
            raise SystemExit(1)

        package_name = available_packages[0].name
        os_name = {
            "debian-10": "buster",
            "debian-11": "bullseye",
            "debian-12": "bookworm",
            "ubuntu-20.04": "focal",
            "ubuntu-22.04": "jammy",
            "ubuntu-24.04": "noble",
            "centos-8": "el8",
            "almalinux-9": "el9",
            "almalinux-10": "el10",
            "sles-15sp3": "sles15sp3",
            "sles-15sp4": "sles15sp4",
            "sles-12sp5": "sles12sp5",
            "sles-15sp5": "sles15sp5",
            "sles-15sp6": "sles15sp6",
            "sles-15sp7": "sles15sp7",
        }.get(distro_name, f"UNKNOWN DISTRO: {distro_name}")
        pkg_pattern = rf"check-mk-{version.edition.long}-{version.version}.*{os_name}.*\.(deb|rpm)"
        if not re.match(f"^{pkg_pattern}$", package_name):
            logger.error("Error: '%s' does not match version=%s", package_name, version)
            logger.error("Error:  (must be '%s')", pkg_pattern)
            raise SystemExit(1)

        logger.info("found %s", available_packages[0])
        return True
    return False


def container_name_suffix(distro_name: str, docker_tag: str) -> str:
    """Container names are (currently) not needed at all but help with finding the context.
    However they need to be informative but unique to avoid conflicts.
    In order to be able to use the same naming scheme for incremental test-image builds soon,
    we put everything in that qualifies a container for a certain scenario (distro, docker_tag,
    Pipfile.lock) but make it 'unique' for now by adding a timestamp"""
    return (
        f"{distro_name}-{docker_tag}"
        f"-{git_commit_id('Pipfile.lock')[:10]}"
        f"-{time.strftime('%Y%m%d%H%M%S')}"
    )


def _create_cmk_image(
    client: docker.DockerClient, distro_name: str, docker_tag: str, version: CMKVersion
) -> str:
    base_image_name_with_tag = f"{_DOCKER_REGISTRY}/{distro_name}:{docker_tag}"
    logger.info("Prepare distro-specific base image [%s]", base_image_name_with_tag)
    if not (base_image := _get_or_load_image(client, base_image_name_with_tag)):
        raise RuntimeError(
            'Image [%s] is not available locally and the registry "%s" is not reachable. It is '
            "not implemented yet to build the image locally. Terminating."
            % (base_image_name_with_tag, _DOCKER_REGISTRY_URL)
        )

    # This installs the requested Checkmk Edition+Version into the new image, for this reason we add
    # these parts to the target image name. The tag is equal to the origin image.
    image_name_with_tag = f"{_DOCKER_REGISTRY}/{distro_name}-{version.edition.short}-{version.version_rc_aware}:{docker_tag}"
    if use_local_package := check_for_local_package(version, distro_name):
        logger.info("+====================================================================+")
        logger.info("| Use locally available package (i.e. don't try to fetch test-image) |")
        logger.info("+====================================================================+")
    else:
        logger.info("+====================================+")
        logger.info("| No locally available package found |")
        logger.info("+====================================+")

        logger.info("Check for available test-image [%s]", image_name_with_tag)
        # First try to get the pre-built image from the local or remote registry
        if (
            (image := _get_or_load_image(client, image_name_with_tag))
            and _is_based_on_current_base_image(image, base_image)
            and _is_using_current_cmk_package(image, version)
        ):
            # We found something locally or remote and ensured it's available locally.
            # Only use it when it's based on the latest available base image. Otherwise
            # skip it. The following code will re-build one based on the current base image
            return image_name_with_tag  # already found, nothing to do.

    logger.info("Build test image [%s] from [%s]", image_name_with_tag, base_image_name_with_tag)

    container_label = {
        "com.checkmk.build_time": f"{int(time.time()):d}",
        "com.checkmk.build_id": base_image.short_id,
        "com.checkmk.base_image": base_image_name_with_tag,
        "com.checkmk.base_image_hash": base_image.short_id,
        "com.checkmk.cmk_edition_short": version.edition.short,
        "com.checkmk.cmk_version": version.version,
        "com.checkmk.cmk_version_rc_aware": version.version_rc_aware,
        "com.checkmk.cmk_branch": version.branch,
        # override the base image label
        "com.checkmk.image_type": "cmk-image",
    }
    # Add information about CI jobs creating these images for easier debugging
    for env_info_key in ("CI_JOB_NAME", "CI_BUILD_NUMBER", "CI_BUILD_URL"):
        if env_info_value := os.environ.get(env_info_key):
            container_label[f"com.checkmk.{env_info_key.lower()}"] = env_info_value

    with _start(
        client,
        # TODO: Re-enable using dedicated container names, the following causes name conflicts:
        # name=f"testbase-{container_name_suffix(distro_name, docker_tag)}",
        image=base_image_name_with_tag,
        labels=container_label,
        command=["tail", "-f", "/dev/null"],  # keep running
        host_config=client.api.create_host_config(
            # needed to make the overlay mounts work on the /git directory
            # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
            privileged=True,
            binds=_image_build_binds(),
        ),
    ) as container:
        logger.info(
            "Building in container %s (from [%s])",
            container.short_id,
            base_image_name_with_tag,
        )

        _exec_run(container, ["mkdir", "-p", "/results"])

        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        _prepare_virtual_environment(container, version)
        _persist_virtual_environment(container, version)

        logger.info("Install Checkmk version")
        _exec_run(
            container,
            ["scripts/run-pipenv", "run", "/git/tests/scripts/install-cmk.py"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        )

        logger.info("Check whether or not installation was OK")
        _exec_run(container, ["ls", "/omd/versions/default"], workdir="/")

        # Now get the hash of the used Checkmk package from the container image and add it to the
        # image labels.
        logger.info("Get Checkmk package hash")
        _exit_code, output = container.exec_run(
            ["cat", str(package_hash_path(version.version, version.edition))],
        )
        hash_entry = output.decode("ascii").strip()
        logger.info("Checkmk package hash entry: %s", hash_entry)

        logger.info("Stopping build container")
        container.stop()
        tmp_image = container.commit()

        new_labels = container.labels.copy()
        new_labels["com.checkmk.cmk_hash"] = hash_entry

        logger.info("Finalizing image")
        labeled_container = client.containers.run(tmp_image, labels=new_labels, detach=True)
        image = labeled_container.commit(image_name_with_tag)
        labeled_container.remove(v=True, force=True)

        logger.info("Commited image [%s] (%s)", image_name_with_tag, image.short_id)
        if not use_local_package and not version.is_release_candidate():
            try:
                logger.info(
                    "Uploading [%s] to registry (%s)",
                    image_name_with_tag,
                    image.short_id,
                )
                client.images.push(image_name_with_tag)
                logger.info("  Upload complete")
            except docker.errors.APIError as e:
                logger.warning("  An error occurred")
                _handle_api_error(e)
        else:
            logger.info("Skipping upload to registry (%s)", image.short_id)

    return image_name_with_tag


def _is_based_on_current_base_image(image: Image, base_image: Image | None) -> bool:
    logger.info("  Check whether or not image is based on the current base image")
    if base_image is None:
        logger.info("  Base image not available, assuming it's up-to-date")
        return False

    image_base_hash = image.labels.get("com.checkmk.base_image_hash")
    if base_image.short_id != image_base_hash:
        logger.info(
            "  Is based on an outdated base image (%s), current is (%s)",
            image_base_hash,
            base_image.short_id,
        )
        return False

    logger.info("  Is based on current base image (%s)", base_image.short_id)
    return True


def _is_using_current_cmk_package(image: Image, version: CMKVersion) -> bool:
    logger.info("  Check whether or not image is using the current Checkmk package")

    cmk_hash_entry = image.labels.get("com.checkmk.cmk_hash")
    if not cmk_hash_entry:
        logger.info("  Checkmk package hash label missing (com.checkmk.cmk_hash). Trigger rebuild.")
        return False

    cmk_hash_image, package_name_image = cmk_hash_entry.split()
    logger.info(
        "  CMK hash of image (%s): %s (%s)",
        image.short_id,
        cmk_hash_image,
        package_name_image,
    )
    cmk_hash_current = get_current_cmk_hash_for_artifact(version, package_name_image)
    logger.info("  Current CMK Hash of artifact: %s (%s)", cmk_hash_current, package_name_image)
    if cmk_hash_current != cmk_hash_image:
        logger.info("  Hashes of docker image and artifact do not match.")
        return False

    logger.info(
        "  Used package hash of image (%s) matches the current one: %s",
        package_name_image,
        cmk_hash_image,
    )
    return True


def get_current_cmk_hash_for_artifact(version: CMKVersion, package_name: str) -> str:
    hash_file_name = f"{package_name}.hash"
    r = requests.get(
        f"https://tstbuilds-artifacts.lan.tribe29.com/{version.version_rc_aware}/{hash_file_name}",
        auth=get_cmk_download_credentials(),
        timeout=30,
    )
    r.raise_for_status()
    hash_name = r.text.split()
    assert len(hash_name) == 2, (
        f"Received multiple entries in hash file for {package_name}: \n" f"{r.text}"
    )
    _hash, package_name_from_hash_file = hash_name
    assert (
        package_name_from_hash_file == package_name
    ), f"The hash file {hash_file_name}'s content ({package_name_from_hash_file}) does not match the expected package name ({package_name})"
    return _hash


def _image_build_binds() -> Mapping[str, DockerBind]:
    if "WORKSPACE" in os.environ:
        logger.info("WORKSPACE set to %s", os.environ["WORKSPACE"])
        return {
            **_runtime_binds(),
            os.path.join(os.environ["WORKSPACE"], "packages"): DockerBind(
                bind="/packages", mode="ro"
            ),
        }
    logger.info("WORKSPACE not set")
    return _runtime_binds()


def _git_repos() -> Mapping[str, DockerBind]:
    checkout_dir = repo_path()
    return {
        **{
            # This ensures that we can also work with git-worktrees and reference clones.
            # For this, the original git repository needs to be mapped into the container as well.
            path: DockerBind(bind=path, mode="ro")
            for path in git_essential_directories(checkout_dir)
        },
        **{
            # To get access to the test scripts and for updating the version from
            # the current git checkout. Will also be used for updating the image with
            # the current git state
            checkout_dir.as_posix(): DockerBind(bind="/git-lowerdir", mode="ro"),
        },
    }


def _runtime_binds() -> Mapping[str, DockerBind]:
    return {
        **_git_repos(),
        # Credentials file for fetching the package from the download server. Used by
        # testlib/version.py in case the version package needs to be downloaded
        # For whatever reason the image can not be started when nothing is mounted
        # at the file mount that was used while building the image. This is not
        # really needed during runtime of the test. We could mount any file.
        (Path(os.environ["HOME"]) / ".cmk-credentials").as_posix(): DockerBind(
            bind="/root/.cmk-credentials",
            mode="ro",
        ),
    }


def _container_env(version: CMKVersion) -> dict[str, str]:
    return {
        "LANG": "C",
        "PIPENV_PIPFILE": "/git/Pipfile",
        "PIPENV_VENV_IN_PROJECT": "true",
        "VERSION": version.version_spec,
        "EDITION": version.edition.short,
        "BRANCH": version.branch,
        "RESULT_PATH": "/results",
        "CI": os.environ.get("CI", ""),
        # Write to this result path by default (may be overridden e.g. by integration tests)
        "PYTEST_ADDOPTS": os.environ.get("PYTEST_ADDOPTS", "") + " --junitxml=/results/junit.xml",
    }


# pep-0692 is not yet finished in mypy...
@contextmanager
def _start(client: docker.DockerClient, **kwargs) -> Iterator[docker.Container]:  # type: ignore[no-untyped-def]
    logger.info("Start new container from [%s] (Args: %s)", kwargs["image"], kwargs)

    try:
        client.images.get(kwargs["image"])
    except docker.errors.ImageNotFound:
        raise Exception("Image [%s] could not be found locally" % kwargs["image"])

    # Start the container with lowlevel API to be able to attach with a debug shell
    # after initialization
    container_id = client.api.create_container(**kwargs)["Id"]
    client.api.start(container_id)
    c: docker.Container = client.containers.get(container_id)

    logger.info("Container ID: %s", c.short_id)

    logger.info("Container is ready")

    try:
        yield c
    finally:
        # Do not leave inactive containers and anonymous volumes behind
        c.remove(v=True, force=True)


# pep-0692 is not yet finished in mypy...
def _exec_run(c: docker.Container, cmd: list[str], check: bool = True, **kwargs) -> int:  # type: ignore[no-untyped-def]
    if kwargs:
        logger.info(
            "Execute in container %s: %r (kwargs: %r)",
            c.short_id,
            subprocess.list2cmdline(cmd),
            kwargs,
        )
    else:
        logger.info("Execute in container %s: %r", c.short_id, subprocess.list2cmdline(cmd))

    result = container_exec(c, cmd, **kwargs)

    if kwargs.get("stream"):
        return result.communicate(line_prefix=b"%s: " % c.short_id.encode("ascii"))

    printed_dot = False
    while result.poll() is None:
        printed_dot = True
        sys.stdout.write(".")
    if printed_dot:
        sys.stdout.write("\n")

    returncode = result.poll()
    if check and returncode != 0:
        raise RuntimeError(f"Command `{' '.join(cmd)}` returned with nonzero exit code")
    return returncode


def container_exec(
    container: docker.Container,
    cmd: str | Sequence[str],
    stdout: bool = True,
    stderr: bool = True,
    stdin: bool = False,
    tty: bool = False,
    privileged: bool = False,
    user: str = "",
    detach: bool = False,
    stream: bool = False,
    socket: bool = False,
    environment: Mapping[str, str] | Sequence[str] | None = None,
    workdir: str | None = None,
) -> ContainerExec:
    """
    An enhanced version of #docker.Container.exec_run() which returns an object
    that can be properly inspected for the status of the executed commands.

    Taken from https://github.com/docker/docker-py/issues/1989. Thanks!
    """

    exec_id: str = container.client.api.exec_create(
        container.id,
        cmd,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        tty=tty,
        privileged=privileged,
        user=user,
        environment=environment,
        workdir=workdir,
    )["Id"]

    output: Iterable[bytes] = container.client.api.exec_start(
        exec_id, detach=detach, tty=tty, stream=stream, socket=socket
    )

    return ContainerExec(container.client, exec_id, output)


class ContainerExec:
    def __init__(
        self, client: docker.DockerClient, container_id: str, output: Iterable[bytes]
    ) -> None:
        self.client = client
        self.id = container_id
        self.output = output

    def inspect(self) -> Mapping:
        return self.client.api.exec_inspect(self.id)  # type: ignore[no-any-return]

    def poll(self) -> int:
        return int(self.inspect()["ExitCode"])

    def communicate(self, line_prefix: bytes = b"") -> int:
        for data in self.output:
            if not data:
                continue

            offset = 0
            while offset < len(data):
                nl = data.find(b"\n", offset)
                if nl >= 0:
                    slce = data[offset : nl + 1]
                    offset = nl + 1
                    sys.stdout.buffer.write(slce)
                    sys.stdout.buffer.write(line_prefix)
                else:
                    slce = data[offset:]
                    offset += len(slce)
                    sys.stdout.buffer.write(slce)
            sys.stdout.flush()
        while self.poll() is None:
            raise RuntimeError()
        return self.poll()


def _copy_directory(
    container: docker.types.containers.Container, src_path: Path, dest_path: Path
) -> None:
    logger.info("Copying %s from container to %s", src_path, dest_path)

    tar_stream = BytesIO()
    bits, _stat = container.get_archive(str(src_path))
    for chunk in bits:
        tar_stream.write(chunk)
    tar_stream.seek(0)

    with tarfile.TarFile(fileobj=tar_stream) as tar:
        tar.extractall(str(dest_path), filter="data")


def _prepare_git_overlay(container: docker.Container, lower_path: str, target_path: str) -> None:
    """Prevent modification of git checkout volume contents

    Create some tmpfs that is mounted as rw layer over the the git checkout
    at /git. All modifications to the git will be lost after the container is
    removed.
    """
    logger.info("Preparing overlay filesystem for %s at %s", lower_path, target_path)
    tmpfs_path = "/git-rw"
    upperdir_path = "%s/upperdir" % tmpfs_path
    workdir_path = "%s/workdir" % tmpfs_path

    # Create mountpoints
    _exec_run(container, ["mkdir", "-p", tmpfs_path, target_path])

    # Prepare the tmpfs as base for the rw-overlay and workdir
    _exec_run(container, ["mount", "-t", "tmpfs", "tmpfs", tmpfs_path])

    # Create directory structure for the overlay
    _exec_run(container, ["mkdir", "-p", upperdir_path, workdir_path])

    # Finally add the overlay mount
    _exec_run(
        container,
        [
            "mount",
            "-t",
            "overlay",
            "overlay",
            "-o",
            f"lowerdir={lower_path},upperdir={upperdir_path},workdir={workdir_path}",
            target_path,
        ],
    )

    # target_path belongs to root, but its content belong to jenkins. Newer git versions don't like
    # that by default, so we explicitly say that this is ok.
    _exec_run(
        container,
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            target_path,
        ],
    )


def _prepare_virtual_environment(container: docker.Container, version: CMKVersion) -> None:
    """Ensure the virtual environment is ready for use

    Because the virtual environment are in the /git path (which is not persisted),
    the initialized virtual environment will be copied to /.venv, which is
    persisted with the image. The test containers may use them.
    """
    _cleanup_previous_virtual_environment(container, version)
    _setup_virtual_environment(container, version)


def _setup_virtual_environment(container: docker.Container, version: CMKVersion) -> None:
    logger.info("Prepare virtual environment")
    _exec_run(
        container,
        ["make", ".venv"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    )

    _exec_run(container, ["test", "-d", "/git/.venv"])


def _cleanup_previous_virtual_environment(container: docker.Container, version: CMKVersion) -> None:
    """Delete existing .venv

    When the git is mounted to the test container for a node which already created it's virtual
    environments in the git directory, the venv may be incompatible with the containers OS. Clean
    up, just to be sure.

    The copied .venv will be used by _reuse_persisted_virtual_environment().
    """
    logger.info("Cleanup previous virtual environments")
    _exec_run(
        container,
        ["rm", "-rf", ".venv"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    )

    _exec_run(container, ["test", "-n", "/.venv"])


def _persist_virtual_environment(container: docker.Container, version: CMKVersion) -> None:
    """Persist the used venv in container image

    Copy the virtual environment that was used during image creation from /git/.venv (not persisted)
    to /.venv (persisted in image). This will be reused later during test executions.
    """
    logger.info("Persisting virtual environments for later use")
    _exec_run(
        container,
        ["rsync", "-aR", ".venv", "/"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    )

    _exec_run(container, ["test", "-d", "/.venv"])


def _reuse_persisted_virtual_environment(container: docker.Container, version: CMKVersion) -> None:
    """Copy /.venv to /git/.venv to reuse previous venv during testing"""
    if (
        _exec_run(
            container,
            ["test", "-d", "/.venv"],
            workdir="/git",
            environment=_container_env(version),
            check=False,
        )
        == 0
    ):
        logger.info("Restore previously created virtual environment")
        _exec_run(
            container,
            ["rsync", "-a", "/.venv", "/git"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        )

    if _mirror_reachable():
        #  Only try to update when the mirror is available, otherwise continue with the current
        #  state, which is good for the most of the time.
        _setup_virtual_environment(container, version)


def _mirror_reachable() -> bool:
    try:
        requests.get(_DOCKER_REGISTRY_URL, timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False
