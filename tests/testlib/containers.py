#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
import sys
import tarfile
import time
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import dockerpty  # type: ignore[import]
import requests
from docker.models.images import Image  # type: ignore[import]

import tests.testlib as testlib
from tests.testlib.version import CMKVersion

import docker  # type: ignore[import]

_DOCKER_REGISTRY = "artifacts.lan.tribe29.com:4000"
_DOCKER_REGISTRY_URL = "https://%s/v2/" % _DOCKER_REGISTRY
# Increase this to enforce invalidation of all existing images
_DOCKER_BUILD_ID = 1

logger = logging.getLogger()


def execute_tests_in_container(
    distro_name: str,
    docker_tag: str,
    version: CMKVersion,
    result_path: Path,
    command: List[str],
    interactive: bool,
) -> int:
    client = _docker_client()
    info = client.info()
    logger.info("Docker version: %s", info["ServerVersion"])

    base_image_name = "%s/%s" % (_DOCKER_REGISTRY, distro_name)
    image_name_with_tag = _create_cmk_image(client, base_image_name, docker_tag, version)

    # Start the container
    with _start(
        client,
        image=image_name_with_tag,
        command="/bin/bash",
        volumes=list(_runtime_volumes().keys()),
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
            binds=[":".join([k, v["bind"], v["mode"]]) for k, v in _runtime_volumes().items()],
            # Our SNMP integration tests need SNMP. For this reason we enable the IPv6 support
            # docker daemon wide, but set some fixed local network which is not being routed.
            # This makes it possible to use IPv6 on the "lo" interface. Externally IPv4 is used
            sysctls={
                "net.ipv6.conf.eth0.disable_ipv6": 1,
            },
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
            logger.info("| Next steps:")
            logger.info("| ")
            logger.info("| /git/scripts/run-pipenv shell")
            logger.info("| cd /git")
            logger.info("| ")
            logger.info("| ... start whatever test you want, for example:")
            logger.info("| ")
            logger.info("| make -C tests test-integration")
            logger.info("| ")
            logger.info("|   Execute all integration tests")
            logger.info("| ")
            logger.info(
                "| tests/scripts/run-integration-test.py "
                "tests/integration/livestatus/test_livestatus.py"
            )
            logger.info("| ")
            logger.info("|   Execute some integration tests")
            logger.info("| ")
            logger.info(
                "| tests/scripts/run-integration-test.py "
                "tests/integration/livestatus/test_livestatus.py "
                "-k test_service_custom_variables "
            )
            logger.info("| ")
            logger.info("|   Execute a single test")
            logger.info("| ")
            logger.info("+-------------------------------------------------")
            dockerpty.start(client.api, container.id)
            return 0

        # Now execute the real test in the container context
        exit_code = _exec_run(
            container,
            command,
            environment=_container_env(version),
            workdir="/git",
            stream=True,
        )

        # Collect the test results located in /results of the container. The
        # jenkins job will make it available as artifact later
        _copy_directory(container, Path("/results"), result_path)

        return exit_code


def _docker_client():
    return docker.from_env(timeout=1200)


def _get_or_load_image(client: docker.DockerClient, image_name_with_tag: str) -> Optional[Image]:
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

        logger.info("  Not in sync with registry (%s), try to pull", registry_data.short_id)

    except docker.errors.ImageNotFound:
        logger.info(
            "  Not available locally, try to pull " "(May take some time. Grab a coffee or two...)"
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


def _get_registry_data(client: docker.DockerClient, image_name_with_tag: str) -> Optional[Image]:
    try:
        registry_data = client.images.get_registry_data(image_name_with_tag)
        return registry_data.pull()
    except docker.errors.NotFound:
        logger.info("  Not available from registry")
        return None
    except docker.errors.APIError as e:
        _handle_api_error(e)
        return None


def _handle_api_error(e):
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


def _create_cmk_image(
    client: docker.DockerClient, base_image_name: str, docker_tag: str, version: CMKVersion
) -> str:
    base_image_name_with_tag = "%s:%s" % (base_image_name, docker_tag)
    logger.info("Preparing base image [%s]", base_image_name_with_tag)
    base_image = _get_or_load_image(client, base_image_name_with_tag)

    # This installs the requested Checkmk Edition+Version into the new image, for this reason we add
    # these parts to the target image name. The tag is equal to the origin image.
    image_name = "%s-%s-%s" % (base_image_name, version.edition_short, version.version)
    image_name_with_tag = "%s:%s" % (image_name, docker_tag)

    logger.info("Preparing image [%s]", image_name_with_tag)
    # First try to get the pre-built image from the local or remote registry
    image = _get_or_load_image(client, image_name_with_tag)
    if (
        image
        and _is_based_on_current_base_image(image, base_image)
        and _is_using_current_cmk_package(image, version)
    ):
        # We found something locally or remote and ensured it's available locally.
        # Only use it when it's based on the latest available base image. Otherwise
        # skip it. The following code will re-build one based on the current base image
        return image_name_with_tag  # already found, nothing to do.

    logger.info("Build image from [%s]", base_image_name_with_tag)
    if base_image is None:
        raise Exception(
            'Image [%s] is not available locally and the registry "%s" is not reachable. It is '
            "not implemented yet to build the image locally. Terminating."
            % (base_image_name_with_tag, _DOCKER_REGISTRY_URL)
        )

    with _start(
        client,
        image=base_image_name_with_tag,
        labels={
            "org.tribe29.build_time": "%d" % time.time(),
            "org.tribe29.build_id": base_image.short_id,
            "org.tribe29.base_image": base_image_name_with_tag,
            "org.tribe29.base_image_hash": base_image.short_id,
            "org.tribe29.cmk_edition_short": version.edition_short,
            "org.tribe29.cmk_version": version.version,
            "org.tribe29.cmk_branch": version.branch(),
            # override the base image label
            "com.tribe29.image_type": "cmk-image",
        },
        command=["tail", "-f", "/dev/null"],  # keep running
        volumes=list(_image_build_volumes().keys()),
        host_config=client.api.create_host_config(
            # needed to make the overlay mounts work on the /git directory
            # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
            privileged=True,
            binds=[":".join([k, v["bind"], v["mode"]]) for k, v in _image_build_volumes().items()],
        ),
    ) as container:
        logger.info(
            "Building in container %s (from [%s])", container.short_id, base_image_name_with_tag
        )

        assert _exec_run(container, ["mkdir", "-p", "/results"]) == 0

        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        _prepare_virtual_environment(container, version)
        _persist_virtual_environment(container, version)

        logger.info("Install Checkmk version")
        assert (
            _exec_run(
                container,
                ["scripts/run-pipenv", "run", "/git/tests/scripts/install-cmk.py"],
                workdir="/git",
                environment=_container_env(version),
                stream=True,
            )
            == 0
        )

        logger.info("Check whether or not installation was OK")
        assert _exec_run(container, ["ls", "/omd/versions/default"], workdir="/") == 0

        # Now get the hash of the used Checkmk package from the container image and add it to the
        # image labels.
        logger.info("Get Checkmk package hash")
        exit_code, output = container.exec_run(
            ["cat", str(testlib.utils.package_hash_path(version.version, version.edition()))],
        )
        assert exit_code == 0
        hash_entry = output.decode("ascii").strip()
        logger.info("Checkmk package hash entry: %s", hash_entry)

        logger.info("Stopping build container")
        container.stop()
        tmp_image = container.commit()

        new_labels = container.labels.copy()
        new_labels["org.tribe29.cmk_hash"] = hash_entry

        logger.info("Finalizing image")
        labeled_container = client.containers.run(tmp_image, labels=new_labels, detach=True)
        image = labeled_container.commit(image_name_with_tag)
        labeled_container.remove(force=True)

        logger.info("Commited image [%s] (%s)", image_name_with_tag, image.short_id)

        try:
            logger.info("Uploading [%s] to registry (%s)", image_name_with_tag, image.short_id)
            client.images.push(image_name_with_tag)
            logger.info("  Upload complete")
        except docker.errors.APIError as e:
            logger.warning("  An error occurred")
            _handle_api_error(e)

    return image_name_with_tag


def _is_based_on_current_base_image(image: Image, base_image: Optional[Image]) -> bool:
    logger.info("  Check whether or not image is based on the current base image")
    if base_image is None:
        logger.info("  Base image not available, assuming it's up-to-date")
        return False

    image_base_hash = image.labels.get("org.tribe29.base_image_hash")
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

    cmk_hash_entry = image.labels.get("org.tribe29.cmk_hash")
    if not cmk_hash_entry:
        logger.info("  Checkmk package hash label missing (org.tribe29.cmk_hash). Trigger rebuild.")
        return False

    current_cmk_hashes = _get_current_cmk_hashes(version)
    if cmk_hash_entry not in current_cmk_hashes:
        logger.info("  Did not find image hash entry (%s) in current hashes", cmk_hash_entry)
        logger.info(current_cmk_hashes)
        return False

    logger.info("  Used package hash (%s) matches the current one", cmk_hash_entry)
    return True


def _get_current_cmk_hashes(version: CMKVersion) -> str:
    r = requests.get(f"https://download.checkmk.com/checkmk/{version.version}/HASHES", timeout=30)
    r.raise_for_status()
    return r.text


def _image_build_volumes():
    volumes = {
        # Credentials file for fetching the package from the download server. Used by
        # testlib/version.py in case the version package needs to be downloaded
        os.path.join(os.environ["HOME"], ".cmk-credentials"): {
            "bind": "/root/.cmk-credentials",
            "mode": "ro",
        },
    }
    if "WORKSPACE" in os.environ:
        volumes[os.path.join(os.environ["WORKSPACE"], "packages")] = {
            "bind": "/packages",
            "mode": "ro",
        }
    volumes.update(_git_repos())
    return volumes


def _git_repos():
    # This ensures that we can also work with git-worktrees. For this, the original git repository
    # needs to be mapped into the container as well.
    repo_path = testlib.repo_path()
    git_entry = os.path.join(repo_path, ".git")
    repos = {
        # To get access to the test scripts and for updating the version from
        # the current git checkout. Will also be used for updating the image with
        # the current git state
        repo_path: {
            "bind": "/git-lowerdir",
            "mode": "ro",
        },
    }
    if os.path.isfile(git_entry):  # if not, it's a directory
        with open(git_entry, "r") as f:
            real_path = f.read()
            real_path = real_path[8:]  # skip "gitdir: "
            real_path = real_path.split("/.git")[0]  # cut off .git/...

        repos[real_path] = {
            "bind": real_path,
            "mode": "ro",
        }

    return repos


def _runtime_volumes():
    volumes = {
        # For whatever reason the image can not be started when nothing is mounted
        # at the file mount that was used while building the image. This is not
        # really needed during runtime of the test. We could mount any file.
        os.path.join(os.environ["HOME"], ".cmk-credentials"): {
            "bind": "/root/.cmk-credentials",
            "mode": "ro",
        }
    }
    volumes.update(_git_repos())
    return volumes


def _container_env(version: CMKVersion) -> Dict[str, str]:
    return {
        "LANG": "C",
        "PIPENV_PIPFILE": "/git/Pipfile",
        "PIPENV_VENV_IN_PROJECT": "true",
        "VERSION": version.version_spec,
        "EDITION": version.edition_short,
        "BRANCH": version.branch(),
        "RESULT_PATH": "/results",
        "CI": os.environ.get("CI", ""),
        # Write to this result path by default (may be overridden e.g. by integration tests)
        "PYTEST_ADDOPTS": os.environ.get("PYTEST_ADDOPTS", "") + " --junitxml=/results/junit.xml",
    }


@contextmanager
def _start(client, **kwargs):
    logger.info("Start new container from [%s] (Args: %s)", kwargs["image"], kwargs)

    try:
        client.images.get(kwargs["image"])
    except docker.errors.ImageNotFound:
        raise Exception("Image [%s] could not be found locally" % kwargs["image"])

    # Start the container with lowlevel API to be able to attach with a debug shell
    # after initialization
    container_id = client.api.create_container(**kwargs)["Id"]
    client.api.start(container_id)
    c = client.containers.get(container_id)

    logger.info("Container ID: %s", c.short_id)

    logger.info("Container is ready")

    try:
        yield c
    finally:
        c.remove(force=True)


def _exec_run(c, cmd, **kwargs):
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

    return result.poll()


def container_exec(
    container,
    cmd,
    stdout=True,
    stderr=True,
    stdin=False,
    tty=False,
    privileged=False,
    user="",
    detach=False,
    stream=False,
    socket=False,
    environment=None,
    workdir=None,
):
    """
    An enhanced version of #docker.Container.exec_run() which returns an object
    that can be properly inspected for the status of the executed commands.

    Taken from https://github.com/docker/docker-py/issues/1989. Thanks!
    """

    exec_id = container.client.api.exec_create(
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

    output = container.client.api.exec_start(
        exec_id, detach=detach, tty=tty, stream=stream, socket=socket
    )

    return ContainerExec(container.client, exec_id, output)


class ContainerExec:
    def __init__(self, client, container_id, output):
        self.client = client
        self.id = container_id
        self.output = output

    def inspect(self):
        return self.client.api.exec_inspect(self.id)

    def poll(self):
        return self.inspect()["ExitCode"]

    def communicate(self, line_prefix=b""):
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
    container: "docker.types.containers.Container", src_path: Path, dest_path: Path
) -> None:
    logger.info("Copying %s from container to %s", src_path, dest_path)

    tar_stream = BytesIO()
    bits, _stat = container.get_archive(str(src_path))
    for chunk in bits:
        tar_stream.write(chunk)
    tar_stream.seek(0)

    with tarfile.TarFile(fileobj=tar_stream) as tar:
        tar.extractall(str(dest_path))


def _prepare_git_overlay(container, lower_path, target_path):
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
    assert _exec_run(container, ["mkdir", "-p", tmpfs_path, target_path]) == 0

    # Prepare the tmpfs as base for the rw-overlay and workdir
    assert (
        _exec_run(
            container,
            ["mount", "-t", "tmpfs", "tmpfs", tmpfs_path],
        )
        == 0
    )

    # Create directory structure for the overlay
    assert _exec_run(container, ["mkdir", "-p", upperdir_path, workdir_path]) == 0

    # Finally add the overlay mount
    assert (
        _exec_run(
            container,
            [
                "mount",
                "-t",
                "overlay",
                "overlay",
                "-o",
                "lowerdir=%s,upperdir=%s,workdir=%s" % (lower_path, upperdir_path, workdir_path),
                target_path,
            ],
        )
        == 0
    )


def _prepare_virtual_environment(container, version):
    """Ensure the virtual environment is ready for use

    Because the virtual environment are in the /git path (which is not persisted),
    the initialized virtual environment will be copied to /.venv, which is
    persisted with the image. The test containers may use them.
    """
    _cleanup_previous_virtual_environment(container, version)
    _setup_virtual_environment(container, version)


def _setup_virtual_environment(container, version):
    logger.info("Prepare virtual environment")
    assert (
        _exec_run(
            container,
            ["make", ".venv"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        )
        == 0
    )

    assert _exec_run(container, ["test", "-d", "/git/.venv"]) == 0


def _cleanup_previous_virtual_environment(container, version):
    """Delete existing .venv

    When the git is mounted to the test container for a node which already created it's virtual
    environments in the git directory, the venv may be incompatible with the containers OS. Clean
    up, just to be sure.

    The copied .venv will be used by _reuse_persisted_virtual_environment().
    """
    logger.info("Cleanup previous virtual environments")
    assert (
        _exec_run(
            container,
            ["rm", "-rf", ".venv"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        )
        == 0
    )

    assert _exec_run(container, ["test", "-n", "/.venv"]) == 0


def _persist_virtual_environment(container, version):
    """Persist the used venv in container image

    Copy the virtual environment that was used during image creation from /git/.venv (not persisted)
    to /.venv (persisted in image). This will be reused later during test executions.
    """
    logger.info("Persisting virtual environments for later use")
    assert (
        _exec_run(
            container,
            ["rsync", "-aR", ".venv", "/"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        )
        == 0
    )

    assert _exec_run(container, ["test", "-d", "/.venv"]) == 0


def _reuse_persisted_virtual_environment(container, version):
    """Copy /.venv to /git/.venv to reuse previous venv during testing"""
    if (
        _exec_run(
            container, ["test", "-d", "/.venv"], workdir="/git", environment=_container_env(version)
        )
        == 0
    ):
        logger.info("Restore previously created virtual environment")
        assert (
            _exec_run(
                container,
                ["rsync", "-a", "/.venv", "/git"],
                workdir="/git",
                environment=_container_env(version),
                stream=True,
            )
            == 0
        )

    if _mirror_reachable():
        #  Only try to update when the mirror is available, otherwise continue with the current
        #  state, which is good for the most of the time.
        _setup_virtual_environment(container, version)


def _mirror_reachable():
    try:
        requests.get(_DOCKER_REGISTRY_URL, timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False
