#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
import tarfile
import logging
import subprocess
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional  # pylint: disable=unused-import

import docker  # type: ignore[import]

import testlib
from testlib.version import CMKVersion

_DOCKER_REGISTRY = "artifacts.lan.tribe29.com:4000"
_DOCKER_REGISTRY_URL = "https://%s/v2/" % _DOCKER_REGISTRY
_DOCKER_IMAGE = "%s/ubuntu-19.04-os-image" % _DOCKER_REGISTRY

logger = logging.getLogger()


def execute_tests_in_container(version, result_path, command):
    # type: (CMKVersion, Path, List[str]) -> int
    client = _docker_client()
    info = client.info()
    logger.info("Docker version: %s", info["ServerVersion"])

    # When invoking the test based on the current git, use the container based on
    # the current daily build. The git is patched into that version later in the
    # test container

    # TODO: Why don't we use our official containers here? We should have all the code
    # ready for using it in either "docker" or "tests-py3/docker" directory.
    image_name = _create_cmk_image(client, _DOCKER_IMAGE, version)

    # Start the container
    with _start(
            client,
            image=image_name,
            # Create some init process that manages signals and processes
            init=True,
            # Important to workaround really high default of docker which results
            # in problems when trying to close all FDs in Python 2.
            ulimits=[
                docker.types.Ulimit(name="nofile", soft=1024, hard=1024),
            ],
            # May be useful for debugging
            #ports={'80/tcp': 3334},
            command=["tail", "-f", "/dev/null"],  # keep running
            volumes=_runtime_volumes(),
            # needed to make the overlay mounts work on the /git directory
            # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
            privileged=True,
    ) as container:
        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        # TODO: Would be nice if we could use the virtualenv from the image building, but it is
        # currently built in a tmpfs overlay volume. We could try to copy it to some other directory
        # in the container and reuse it here.
        _prepare_virtual_environments(container, version)

        # Now execute the real crawl test.  It will create a site "crawl_central"
        # and start to crawl all reachable GUI pages. Print the output during the
        # execution of the test.
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
    return docker.from_env()


def _get_or_load_image(client, image_name):
    # type: (docker.DockerClient, str) -> Optional[docker.Image]
    try:
        image = client.images.get(image_name)
        logger.info("Image %s is already available locally (%s)", image_name, image.short_id)
        return image
    except docker.errors.ImageNotFound:
        logger.info("Image %s is not available locally, trying to download from registry",
                    image_name)

    try:
        image = client.images.pull("%s:latest" % image_name)
        logger.info("Image %s has been loaded from registry (%s)", image_name, image.short_id)
        return image
    except docker.errors.NotFound:
        logger.info("Image %s is not available from registry", image_name)
    except docker.errors.APIError as e:
        if "no basic auth" in "%s" % e:
            raise Exception(
                "No authentication information stored for %s. You will have to login to the "
                "registry using \"docker login %s\" to be able to execute the tests." %
                (_DOCKER_REGISTRY, _DOCKER_REGISTRY_URL))
        if "request canceled while waiting for connection" in "%s" % e:
            return None
        raise

    return None


def _create_cmk_image(client, base_image_name, version):
    # type: (docker.DockerClient, str, CMKVersion) -> str
    image_name = "%s-%s-%s-%s" % (base_image_name, version.edition_short, version.version,
                                  version.branch())

    logger.info("Preparing %s image from %s", image_name, base_image_name)
    # First try to get the image from the local or remote registry
    # TODO: How to handle image updates?
    image = _get_or_load_image(client, image_name)
    if image:
        return image_name  # already found, nothing to do.

    logger.info("Create new image %s from %s", image_name, base_image_name)
    # TODO: How to handle image updates?
    base_image = _get_or_load_image(client, base_image_name)
    if base_image is None:
        raise Exception(
            "Image %s is not available locally and the registry \"%s\" is not reachable. It is "
            "not implemented yet to build the image locally. Terminating." %
            (base_image_name, _DOCKER_REGISTRY_URL))

    #container = client.containers.run(
    #    image=base_image,
    #    command=["tail", "-f", "/dev/null"],  # keep running
    #    volumes=_image_build_volumes(),
    #    detach=True,
    #    # needed to make the overlay mounts work on the /git directory
    #    # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
    #    privileged=True,
    #)
    with _start(
            client,
            image=base_image_name,
            command=["tail", "-f", "/dev/null"],  # keep running
            volumes=_image_build_volumes(),
            # needed to make the overlay mounts work on the /git directory
            # Should work, but does not seem to be enough: 'cap_add=["SYS_ADMIN"]'. Using this instead:
            privileged=True,
    ) as container:

        logger.info("Building in container %s (created from %s)", container.short_id,
                    base_image_name)

        assert _exec_run(container, ["mkdir", "-p", "/results"]) == 0

        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git")
        _prepare_virtual_environments(container, version)

        logger.info("Install Checkmk version")
        assert _exec_run(
            container,
            ["scripts/run-pipenv", "3", "run", "/git/tests-py3/gui_crawl/install-cmk.py"],
            workdir="/git",
            environment=_container_env(version),
            stream=True,
        ) == 0

        logger.info("Check whether or not installation was OK")
        assert _exec_run(
            container,
            ["ls", "/omd/versions/default"],
            workdir="/",
        ) == 0

        logger.info("Finalizing image")

        container.stop()

        image = container.commit(image_name)
        logger.info("Commited image %s (%s)", image_name, image.short_id)

        # TODO: Push image to the registry?

    return image_name


def _image_build_volumes():
    return {
        # To get access to the test scripts and for updating the version from
        # the current git checkout. Will also be used for updating the image with
        # the current git state
        testlib.repo_path(): {
            "bind": "/git-lowerdir",
            "mode": "ro",
        },
        # Used to gather the Checkmk package from. In case it is not available
        # the package will be downloaded from the download server
        "/bauwelt/download": {
            "bind": "/bauwelt/download",
            "mode": "ro",
        },
        # Credentials file for fetching the package from the download server. Used by
        # testlib/version.py in case the version package needs to be downloaded
        "%s/.cmk-credentials" % os.environ["HOME"]: {
            "bind": "/root/.cmk-credentials",
            "mode": "ro",
        }
    }


def _runtime_volumes():
    return {
        # To get access to the test scripts and for updating the version from
        # the current git checkout. Will also be used for updating the image with
        # the current git state
        testlib.repo_path(): {
            "bind": "/git-lowerdir",
            "mode": "ro",
        },
        # For whatever reason the image can not be started when nothing is mounted
        # at the file mount that was used while building the image. This is not
        # really needed during runtime of the test. We could mount any file.
        "%s/.cmk-credentials" % os.environ["HOME"]: {
            "bind": "/root/.cmk-credentials",
            "mode": "ro",
        }
    }


def _container_env(version):
    # type: (CMKVersion) -> Dict[str, str]
    return {
        "LANG": "C",
        "PIPENV_PIPFILE": "/git/Pipfile",
        "PIPENV_VENV_IN_PROJECT": "true",
        "VERSION": version.version,
        "EDITION": version.edition_short,
        "BRANCH": version.branch(),
        "RESULT_PATH": "/results",
    }


@contextmanager
def _start(client, **kwargs):
    logger.info("Start new container from %s (Args: %s)", kwargs["image"], kwargs)

    try:
        client.images.get(kwargs["image"])
    except docker.errors.ImageNotFound:
        raise Exception("Image %s could not be found locally" % kwargs["image"])

    c = client.containers.run(detach=True, **kwargs)
    logger.info("Container ID: %s", c.short_id)

    logger.info("Container is ready")

    try:
        yield c
    finally:
        c.remove(force=True)


def _exec_run(c, cmd, **kwargs):
    if kwargs:
        logger.info("Execute in container %s: %r (kwargs: %r)", c.short_id,
                    subprocess.list2cmdline(cmd), kwargs)
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


def container_exec(container,
                   cmd,
                   stdout=True,
                   stderr=True,
                   stdin=False,
                   tty=False,
                   privileged=False,
                   user='',
                   detach=False,
                   stream=False,
                   socket=False,
                   environment=None,
                   workdir=None):
    """
    An enhanced version of #docker.Container.exec_run() which returns an object
    that can be properly inspected for the status of the executed commands.

    Taken from https://github.com/docker/docker-py/issues/1989. Thanks!
    """

    exec_id = container.client.api.exec_create(container.id,
                                               cmd,
                                               stdout=stdout,
                                               stderr=stderr,
                                               stdin=stdin,
                                               tty=tty,
                                               privileged=privileged,
                                               user=user,
                                               environment=environment,
                                               workdir=workdir)['Id']

    output = container.client.api.exec_start(exec_id,
                                             detach=detach,
                                             tty=tty,
                                             stream=stream,
                                             socket=socket)

    return ContainerExec(container.client, exec_id, output)


class ContainerExec(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, client, container_id, output):
        self.client = client
        self.id = container_id
        self.output = output

    def inspect(self):
        return self.client.api.exec_inspect(self.id)

    def poll(self):
        return self.inspect()['ExitCode']

    def communicate(self, line_prefix=b''):
        for data in self.output:
            if not data:
                continue

            offset = 0
            while offset < len(data):
                sys.stdout.buffer.write(line_prefix)
                nl = data.find(b'\n', offset)
                if nl >= 0:
                    slce = data[offset:nl + 1]
                    offset = nl + 1
                else:
                    slce = data[offset:]
                    offset += len(slce)
                sys.stdout.buffer.write(slce)
            sys.stdout.flush()
        while self.poll() is None:
            raise RuntimeError()
        return self.poll()


def _copy_directory(container, src_path, dest_path):
    # type: (docker.types.containers.Container, Path, Path) -> None
    logger.info("Copying %s from container to %s", src_path, dest_path)

    tar_stream = BytesIO()
    bits, _stat = container.get_archive(str(src_path))
    for chunk in bits:
        tar_stream.write(chunk)
    tar_stream.seek(0)

    tar = tarfile.TarFile(fileobj=tar_stream)
    tar.extractall(str(dest_path))


def _prepare_git_overlay(container, lower_path, target_path):
    logger.info("Preparing overlay filesystem for %s at %s", lower_path, target_path)
    tmpfs_path = "/git-rw"
    upperdir_path = "%s/upperdir" % tmpfs_path
    workdir_path = "%s/workdir" % tmpfs_path

    # Create mountpoints
    assert _exec_run(container, ["mkdir", "-p", tmpfs_path, target_path]) == 0

    # Prepare the tmpfs as base for the rw-overlay and workdir
    assert _exec_run(
        container,
        ["mount", "-t", "tmpfs", "tmpfs", tmpfs_path],
    ) == 0

    # Create directory structure for the overlay
    assert _exec_run(container, ["mkdir", "-p", upperdir_path, workdir_path]) == 0

    # Finally add the overlay mount
    assert _exec_run(
        container,
        [
            "mount", "-t", "overlay", "overlay", "-o",
            "lowerdir=%s,upperdir=%s,workdir=%s" %
            (lower_path, upperdir_path, workdir_path), target_path
        ],
    ) == 0


def _prepare_virtual_environments(container, version):
    # When the git is mounted to the crawl container for a node which already
    # created it's virtual environments these may be incopatible with the
    # containers OS. Clean up, just to be sure.
    logger.info("Cleanup previous virtual environments")
    assert _exec_run(
        container,
        ["rm", "-rf", "virtual-envs/3.7/.venv"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    ) == 0

    logger.info("Prepare virtual environment")
    assert _exec_run(
        container,
        ["make", ".venv-3.7"],
        workdir="/git",
        environment=_container_env(version),
        stream=True,
    ) == 0
