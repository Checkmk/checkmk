#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import subprocess
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Union

import docker  # type: ignore[import-untyped]
import requests

from tests.testlib import repo_path
from tests.testlib.utils import wait_until
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger()

build_path = str(repo_path() / "docker_image")
image_prefix = "docker-tests"
distro_codename = "jammy"


def cleanup_old_packages() -> None:
    """Cleanup files created by _prepare_package during previous job executions"""
    for p in Path(build_path).glob("*.deb"):
        logger.info("Cleaning up old package %s", p)
        p.unlink()


def get_container_ip(c: docker.models.containers.Container) -> str:
    """Return the primary IP address for a given container name."""
    output = f"{c.attrs['NetworkSettings']['IPAddress']}" or "127.0.0.1"

    return output


def image_name(version: CMKVersion) -> str:
    return f"docker-tests/check-mk-{version.edition.long}-{version.branch}-{version.version}"


def package_name(version: CMKVersion) -> str:
    return f"check-mk-{version.edition.long}-{version.version}_0.{distro_codename}_amd64.deb"


def prepare_build() -> None:
    assert subprocess.run(["make", "needed-packages"], cwd=build_path, check=False).returncode == 0


def prepare_package(version: CMKVersion) -> None:
    """On Jenkins copies a previously built package to the build path."""
    if "WORKSPACE" not in os.environ:
        logger.info("Not executed on CI: Do not prepare a Checkmk .deb in %s", build_path)
        return

    source_package_path = Path(
        os.environ["WORKSPACE"],
        "downloaded_packages_for_docker_tests",
        version.version,
        package_name(version),
    )
    test_package_path = Path(build_path, package_name(version))

    logger.info("Executed on CI: Preparing package %s", test_package_path)

    if (
        test_package_path.exists()
        and test_package_path.stat().st_mtime >= source_package_path.stat().st_mtime
    ):
        logger.info("File already exists - Fine")
        return

    cleanup_old_packages()

    logger.info("Copying from %s", source_package_path)
    test_package_path.write_bytes(source_package_path.read_bytes())


def pull_checkmk(
    client: docker.DockerClient, version: CMKVersion
) -> docker.models.containers.Image:
    if not version.is_raw_edition():
        raise Exception("Can only fetch raw edition at the moment")

    logger.info("Downloading docker image: checkmk/check-mk-raw:%s", version.version)
    return client.images.pull("checkmk/check-mk-raw", tag=version.version)


def resolve_image_alias(alias: str) -> str:
    """Resolves given "Docker image alias" using the common `resolve.py` and returns an image
    name which can be used with `docker run`
    >>> image = resolve_image_alias("IMAGE_CMK_BASE")
    >>> assert image and isinstance(image, str)
    """
    return subprocess.check_output(
        [os.path.join(repo_path(), "buildscripts/docker_image_aliases/resolve.py"), alias],
        text=True,
    ).split("\n", maxsplit=1)[0]


def build_checkmk(
    client: docker.DockerClient,
    version: CMKVersion,
    prepare_pkg: bool = True,
) -> tuple[docker.models.containers.Image, Mapping[str, str]]:
    prepare_build()

    if prepare_pkg:
        prepare_package(version)

    logger.info("Building docker image (or reuse existing): %s", image_name(version))
    try:
        image: docker.models.containers.Image
        build_logs: Mapping[str, str]
        image, build_logs = client.images.build(
            path=build_path,
            tag=image_name(version),
            buildargs={
                "CMK_VERSION": version.version,
                "CMK_EDITION": version.edition.long,
                "IMAGE_CMK_BASE": resolve_image_alias("IMAGE_CMK_BASE"),
            },
        )
    except docker.errors.BuildError as e:
        logger.error("= Build log ==================")
        for entry in e.build_log:
            if "stream" in entry:
                logger.error(entry["stream"].rstrip())
            elif "errorDetail" in entry:
                continue  # Is already part of the exception message
            else:
                logger.error("UNEXPECTED FORMAT: %r", entry)
        logger.error("= Build log ==================")
        raise

    logger.info("(Set pytest log level to DEBUG (--log-cli-level=DEBUG) to see the build log)")
    for entry in build_logs:
        if "stream" in entry:
            logger.debug(entry["stream"].rstrip())
        elif "aux" in entry:
            logger.debug(entry["aux"])
        else:
            logger.debug("UNEXPECTED FORMAT: %r", entry)
    logger.debug("= Build log ==================")

    logger.info("Built image: %s", image.short_id)
    attrs = image.attrs
    config = attrs["Config"]

    assert config["Labels"] == {
        "org.opencontainers.image.vendor": "Checkmk GmbH",
        "org.opencontainers.image.version": version.version,
        "maintainer": "feedback@checkmk.com",
        "org.opencontainers.image.description": "Checkmk is a leading tool for Infrastructure & Application Monitoring",
        "org.opencontainers.image.ref.name": "ubuntu",  # TODO: investigate who sets this
        "org.opencontainers.image.source": "https://github.com/checkmk/checkmk",
        "org.opencontainers.image.title": "Checkmk",
        "org.opencontainers.image.url": "https://checkmk.com/",
    }

    assert config["Env"] == [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "CMK_SITE_ID=cmk",
        "CMK_LIVESTATUS_TCP=",
        "CMK_PASSWORD=",
        "MAIL_RELAY_HOST=",
        "CMK_CONTAINERIZED=TRUE",
    ]

    assert "Healthcheck" in config

    assert attrs["ContainerConfig"]["Entrypoint"] == ["/docker-entrypoint.sh"]

    assert attrs["ContainerConfig"]["ExposedPorts"] == {
        "5000/tcp": {},
        "6557/tcp": {},
    }

    # 2018-11-14: 900 -> 920
    # 2018-11-22: 920 -> 940
    # 2019-04-10: 940 -> 950
    # 2019-07-12: 950 -> 1040 (python3)
    # 2019-07-27: 1040 -> 1054 (numpy)
    # 2019-11-15: Temporarily disabled because of Python2 => Python3 transition
    #    assert attrs["Size"] < 1110955410.0, \
    #        "Docker image size increased: Please verify that this is intended"

    assert len(attrs["RootFS"]["Layers"]) == 6

    return image, build_logs


@contextmanager
def start_checkmk(
    client: docker.DockerClient,
    version: CMKVersion | None = None,
    is_update: bool = False,
    site_id: str = "cmk",
    name: str | None = None,
    hostname: str | None = None,
    environment: dict[str, str] | None = None,
    ports: dict[str, Union[int, None, tuple[str, int] | list[int]]] | None = None,
    volumes: list[str] | None = None,
    volumes_from: list[str] | None = None,
) -> Iterator[docker.models.containers.Container]:
    """Provide a readily configured Checkmk docker container."""
    if version is None:
        version = version_from_env()

    try:
        if version.version == version_from_env().version:
            _image, _build_logs = build_checkmk(client, version)
        else:
            # In case the given version is not the current branch version, don't
            # try to build it. Download it instead!
            _image = pull_checkmk(client, version)
    except requests.exceptions.ConnectionError as e:
        raise Exception(
            "Failed to access docker socket (Permission denied). You need to be member of the "
            'docker group to get access to the socket (e.g. use "make -C docker_image setup") to '
            "fix this, then restart your computer and try again."
        ) from e

    kwargs = {
        key: value
        for key, value in {
            "name": name,
            "hostname": hostname,
            "environment": environment,
            "ports": ports,
            "volumes": volumes,
            "volumes_from": volumes_from,
        }.items()
        if value is not None
    }
    c = client.containers.run(image=_image.id, detach=True, **kwargs)
    logger.info("Starting container %s from image %s", c.short_id, _image.short_id)

    try:
        site_id = (environment or {}).get("CMK_SITE_ID", site_id)
        wait_until(lambda: "### CONTAINER STARTED" in c.logs().decode("utf-8"), timeout=120)
        output = c.logs().decode("utf-8")

        if not is_update:
            assert "Created new site" in output
            assert "cmkadmin with password:" in output
        else:
            assert "Created new site" not in output
            assert "cmkadmin with password:" not in output

        assert "STARTING SITE" in output

        status_rc, status_output = c.exec_run(["omd", "status"], user=site_id)
        assert status_rc == 0, f"Status is {status_rc}. Output: {status_output.decode('utf-8')}"
    except:
        logger.error(c.logs().decode("utf-8"))
        raise

    # reload() to make sure all attributes are set (e.g. NetworkSettings)
    c.reload()

    logger.debug(c.logs().decode("utf-8"))

    try:
        yield c
    finally:
        if os.getenv("CLEANUP", "1") == "1":
            c.remove(force=True)
