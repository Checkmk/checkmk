#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Module for managing Checkmk Docker containers in integration tests.

This module provides utilities for:
- Preparing and cleaning Checkmk packages for Docker containers,
- Building and pulling Docker images with required configurations,
- Copying files and sending input to containers,
- Resolving Docker image aliases,
- Extracting container IPs.
- the CheckmkApp class for managing Checkmk application containers.
"""

import io
import logging
import os
import subprocess
import tarfile
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from socket import SocketIO
from typing import Any, Final, Literal, Self, TypeAlias, TypedDict

import docker.client
import docker.errors
import docker.models
import docker.models.containers
import docker.models.images
import requests

from cmk.crypto.password import Password
from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.openapi_session import AgentReceiverApiSession, CMKOpenApiSession
from tests.testlib.package_manager import ABCPackageManager
from tests.testlib.utils import is_cleanup_enabled
from tests.testlib.version import (
    CMKPackageInfo,
    CMKPackageInfoOld,
    edition_from_env,
    version_from_env,
)

logger = logging.getLogger()

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

build_path = repo_path() / "docker_image"
image_prefix = "docker-tests"
DISTRO_CODENAME: Final = "jammy"  # ubuntu-22.04
cse_config_root = Path("/tmp/cmk-docker-test/cse-config-volume")


def cleanup_old_packages() -> None:
    """Cleanup files created by _prepare_package during previous job executions"""
    for p in build_path.glob("*.deb"):
        logger.info("Cleaning up old package %s", p)
        p.unlink()


def copy_to_container(
    c: docker.models.containers.Container,
    source: str | Path,
    target: str | Path,
) -> bool:
    """Copy a source file to the target folder in the container."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w|") as tar, open(source, "rb") as f:
        info = tar.gettarinfo(fileobj=f)
        info.name = os.path.basename(source)
        tar.addfile(info, f)

    return bool(c.put_archive(Path(target).as_posix(), stream.getvalue()))


def get_container_ip(c: docker.models.containers.Container) -> str:
    """Return the primary IP address for a given container."""
    network_settings = c.attrs["NetworkSettings"]
    container_ip: str = network_settings.get(
        "IPAddress",
        next(
            (
                network_settings["Networks"][network].get("IPAddress")
                for network in network_settings.get("Networks", [])
            ),
            "127.0.0.1",
        ),
    )

    return container_ip


def send_to_container(c: docker.models.containers.Container, text: str) -> None:
    """Send text to the STDIN of a given container."""
    s = c.attach_socket(params={"stdin": 1, "stream": 1})

    if not isinstance(s, SocketIO):
        raise TypeError(f"Expected SocketIO, got {type(s)}")

    s.write(text.encode("utf-8"))
    s.close()


def image_name(package_info: CMKPackageInfo | CMKPackageInfoOld) -> str:
    return (
        "docker-tests/check-mk-"
        f"{package_info.edition.long}-{package_info.version.branch}-{package_info.version.version}"
    )


def package_name(package_info: CMKPackageInfo | CMKPackageInfoOld) -> str:
    """Return full name of a debian-based Checkmk package."""
    return (
        f"check-mk-{package_info.edition.long}-{package_info.version.version}_0"
        f".{DISTRO_CODENAME}_amd64.deb"
    )


def prepare_build() -> None:
    assert subprocess.run(["make", "needed-packages"], cwd=build_path, check=False).returncode == 0


def prepare_package(package_info: CMKPackageInfo | CMKPackageInfoOld) -> None:
    """On Jenkins copies a previously built package to the build path."""
    pkg_name = package_name(package_info)
    test_package_path = build_path / pkg_name
    if "WORKSPACE" not in os.environ:
        if test_package_path.exists():
            logger.info("Checkmk package already exists at %s!", test_package_path)
        else:
            # download CMK installation package for use in container
            ABCPackageManager.factory().download(target_folder=build_path)
        return

    source_package_path = Path(
        os.environ["WORKSPACE"],
        "downloaded_packages_for_docker_tests",
        package_info.version.version,
        pkg_name,
    )

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
    client: docker.client.DockerClient,
    package_info: CMKPackageInfo | CMKPackageInfoOld,
) -> docker.models.images.Image:
    if not package_info.edition.is_community_edition():
        raise Exception("Can only fetch community edition at the moment")
    image_name = f"checkmk/check-mk-{package_info.edition.long}"
    logger.info("Downloading docker image: %s:%s", image_name, package_info.version.version)
    return client.images.pull(image_name, tag=package_info.version.version)


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
    client: docker.client.DockerClient,
    package_info: CMKPackageInfo | CMKPackageInfoOld,
    prepare_pkg: bool = True,
) -> tuple[docker.models.images.Image, Iterator[JSON]]:
    """Builds (or reuses) and verifies a docker image for a given Checkmk version.

    Args:
        client (docker.client.DockerClient): the used docker client
        version (CMKVersion): the Checkmk version to build the image for
        prepare_pkg (bool, optional): Also pull CMK packages; see prepare_package. Defaults to True.

    Returns:
        tuple[docker.models.images.Image, Iterator[JSON]: the docker image and
            the docker build logs
    """
    prepare_build()

    if prepare_pkg:
        prepare_package(package_info)

    logger.info("Building docker image (or reuse existing): %s", image_name(package_info))
    try:
        image, build_logs = client.images.build(
            path=build_path.as_posix(),
            tag=image_name(package_info),
            buildargs={
                "CMK_VERSION": package_info.version.version,
                "CMK_EDITION": package_info.edition.long,
                "IMAGE_CMK_BASE": resolve_image_alias("IMAGE_CMK_BASE"),
            },
        )
    except docker.errors.BuildError as e:
        logger.error("= Build log ==================")
        for entry in e.build_log:
            if "stream" in entry:
                logger.error(entry["stream"].rstrip())
            elif "errorDetail" not in entry:
                logger.error("UNEXPECTED FORMAT: %r", entry)
        logger.error("= Build log ==================")
        raise

    logger.info("(Set pytest log level to DEBUG (--log-cli-level=DEBUG) to see the build log)")

    for logs_entry in build_logs:
        if not isinstance(logs_entry, dict):
            logger.debug("UNEXPECTED FORMAT: %r", logs_entry)
        elif "stream" in logs_entry and isinstance(logs_entry["stream"], str):
            logger.debug(logs_entry["stream"].rstrip())
        elif "aux" in logs_entry:
            logger.debug(logs_entry["aux"])
        else:
            logger.debug("UNEXPECTED FORMAT: %r", logs_entry)

    logger.debug("= Build log ==================")

    logger.info("Built image: %s", image.short_id)
    attrs = image.attrs
    config = attrs["Config"]

    assert config["Labels"] == {
        "org.opencontainers.image.vendor": "Checkmk GmbH",
        "org.opencontainers.image.version": package_info.version.version,
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
        "TZ=",
        "CMK_CONTAINERIZED=TRUE",
    ]

    assert "Healthcheck" in config

    assert config["Entrypoint"] == ["/docker-entrypoint.sh"]

    assert config["ExposedPorts"] == {
        "5000/tcp": {},
        "6557/tcp": {},
    }

    assert len(attrs["RootFS"]["Layers"]) == 6

    return image, build_logs


class CheckmkApp:
    """A Checkmk application docker container usable for testing.

    It encapsulates the lifecycle of a Checkmk application container,
    including site initialization, OpenAPI session setup, agent installation, and registration.

    The module supports both raw and SaaS editions of Checkmk.
    """

    def __init__(
        self,
        client: docker.client.DockerClient,
        package_info: CMKPackageInfo | CMKPackageInfoOld | None = None,
        is_update: bool = False,
        site_id: str = "cmk",
        name: str | None = None,
        hostname: str | None = None,
        environment: dict[str, str] | None = None,
        ports: dict[str, int | None | tuple[str, int] | list[int]] | None = None,
        volumes: list[str] | None = None,
        volumes_from: list[str] | None = None,
        password: str = "cmk",
    ):
        # docker container defaults
        self.username = "cmkadmin"
        self.password = password
        self.port = 5000
        self.agent_receiver_port = 8000
        self.api_version = "1.0"
        self.api_user = "cmkapi"
        self.api_secret = Password.random(24).raw

        self.client = client
        self.name = name
        self.hostname = hostname
        self.site_id = site_id
        self.site_root = f"/omd/sites/{self.site_id}"
        self.package_info = package_info or CMKPackageInfo(version_from_env(), edition_from_env())
        self.environment = {"CMK_PASSWORD": self.password, "CMK_SITE_ID": self.site_id} | (
            environment or {}
        )
        self.is_update = is_update
        self.ports = ports
        _volumes = volumes or []
        if self.package_info.edition.is_cloud_edition():
            _volumes += self._get_cse_volumes(cse_config_root)
        self.volumes = _volumes if _volumes else None
        self.volumes_from = volumes_from

        self.container = self._setup()
        self.ip = get_container_ip(self.container)

        self.url = f"http://{self.ip}:{self.port}"

        # setup openapi session
        self.openapi = CMKOpenApiSession(
            host=self.ip,
            user=self.username,
            password=self.password,
            site_version=self.package_info.version,
            site_edition=self.package_info.edition,
            port=self.port,
            site=self.site_id,
            api_version=self.api_version,
        )
        self.openapi_agent_receiver = AgentReceiverApiSession(
            openapi_session=self.openapi,
        )
        self._create_automation_user()

    @property
    def logs(self) -> str:
        return self.container.logs().decode("utf-8")

    def _setup(self) -> docker.models.containers.Container:
        """Provide a readily configured Checkmk docker container."""

        try:
            if self.package_info.version.version == version_from_env().version:
                _image, _build_logs = build_checkmk(self.client, self.package_info)
            else:
                # In case the given version is not the current branch version, don't
                # try to build it. Download it instead!
                _image = pull_checkmk(self.client, self.package_info)
        except requests.exceptions.ConnectionError as e:
            raise Exception(
                "Failed to access docker socket (Permission denied). You need to be member of the"
                ' docker group to get access to the socket (e.g. use "make -C docker_image setup")'
                " to fix this, then restart your computer and try again."
            ) from e

        if self.package_info.edition.is_cloud_edition():
            from tests.testlib.nonfree.cloud.utils import (  # type: ignore[import-untyped, unused-ignore]
                create_cse_initial_config,
            )

            create_cse_initial_config(root=Path(cse_config_root))

        try:
            if self.name is None:
                raise docker.errors.NullResource("No container name specified")

            c = self.client.containers.get(self.name)
            if os.getenv("REUSE") == "1":
                logger.info("Reusing existing container %s", c.short_id)
                c.start()
                c.exec_run(["omd", "start"], user=self.site_id)
            else:
                logger.info("Removing existing container %s", c.short_id)
                c.remove(force=True)
                self._remove_volumes()
                raise docker.errors.NotFound(self.name)
        except (docker.errors.NotFound, docker.errors.NullResource):

            class RunContainersKwargs(TypedDict, total=False):
                name: str
                hostname: str
                environment: dict[str, str]
                ports: dict[str, int | None | tuple[str, int] | list[int]]
                volumes: list[str]
                volumes_from: list[str]

            kwargs = RunContainersKwargs(environment=self.environment)

            if self.name is not None:
                kwargs["name"] = self.name

            if self.hostname is not None:
                kwargs["hostname"] = self.hostname

            if self.ports is not None:
                kwargs["ports"] = self.ports

            if self.volumes is not None:
                kwargs["volumes"] = self.volumes

            if self.volumes_from is not None:
                kwargs["volumes_from"] = self.volumes_from

            try:
                c = self.client.containers.run(image=_image, detach=True, **kwargs)
            except Exception as e:
                raise Exception(f"Failed to start container from image {_image.short_id}!") from e
            logger.info("Starting container %s from image %s", c.short_id, _image.short_id)

            try:
                self.site_id = self.environment.get("CMK_SITE_ID", self.site_id)
                wait_until(lambda: "### CONTAINER STARTED" in c.logs().decode("utf-8"), timeout=120)
                output = c.logs().decode("utf-8")

                assert ("Created new site" in output) != self.is_update
                assert ("cmkadmin with password:" in output) != self.is_update

                assert "STARTING SITE" in output
            except TimeoutError:
                logger.error(
                    "TIMEOUT while starting Checkmk. Log output: %s", c.logs().decode("utf-8")
                )
                raise

        status_rc, status_output = c.exec_run(["omd", "status"], user=self.site_id)
        assert status_rc == 0, f"Status is {status_rc}. Output: {status_output.decode('utf-8')}"

        # reload() to make sure all attributes are set (e.g. NetworkSettings)
        c.reload()

        self.ports = {
            str(port): c.attrs["NetworkSettings"]["Ports"][str(port)][0]["HostPort"]
            for port in self.ports or []
        }

        logger.debug(c.logs().decode("utf-8"))

        # TODO: add Checkmk Cloud auth provider setup

        return c

    def _teardown(self) -> None:
        if is_cleanup_enabled():
            self.container.stop()
            self.container.remove(force=True)
            self._remove_volumes()

    @staticmethod
    def _get_cse_volumes(config_root: Path) -> list[str]:
        cse_config_dir = Path("etc/cse")
        cse_config_on_local_machine = config_root / cse_config_dir
        cse_config_on_container = Path("/") / cse_config_dir
        return [f"{cse_config_on_local_machine}:{cse_config_on_container}:ro"]

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any
    ) -> None:
        self._teardown()

    def _create_automation_user(self) -> None:
        if self.openapi.users.get(self.api_user):
            logger.info("Dropping existing test-user: '%s'", self.api_user)
            self.openapi.users.delete(self.api_user)
        logger.info("Creating automation user: '%s'.", self.api_user)
        self.openapi.users.create(
            username=self.api_user,
            fullname="Automation user for tests",
            password=self.api_secret,
            email="automation@localhost",
            contactgroups=[],
            roles=["admin"],
            is_automation_user=True,
        )
        self.openapi.changes.activate_and_wait_for_completion()
        self.openapi.set_authentication_header(user=self.api_user, password=self.api_secret)

    def _remove_volumes(self) -> None:
        volume_ids = [_.split(":")[0] for _ in self.volumes or []]
        exceptions: list[type[docker.errors.APIError]] = [docker.errors.NotFound]
        if self.is_update:
            exceptions.append(docker.errors.APIError)
        with suppress(*exceptions):
            for volume_id in volume_ids:
                self.client.volumes.get(volume_id).remove(force=True)

    def install_agent(
        self, app: docker.models.containers.Container, agent_type: Literal["rpm", "deb"] = "deb"
    ) -> None:
        """Download an agent from Checkmk container and install it into an application container."""
        agent_os = "linux"
        os_type = f"{agent_os}_{agent_type}"
        agent_path = f"/tmp/check_mk_agent.{agent_type}"

        logger.info('Downloading Checkmk agent "%s"...', agent_path)
        with open(agent_path, "wb") as agent_file:
            agent_file.write(
                self.openapi.get(
                    "/domain-types/agent/actions/download/invoke",
                    params={"os_type": os_type},
                    headers={"Accept": "application/octet-stream"},
                ).content
            )

        logger.info('Installing Checkmk agent "%s"...', agent_path)
        assert copy_to_container(app, agent_path, "/")
        install_agent_rc, install_agent_output = app.exec_run(
            f"{'rpm' if agent_type == 'rpm' else 'dpkg'} --install '/{os.path.basename(agent_path)}'",
            user="root",
        )
        assert install_agent_rc == 0, (
            f"Error during agent installation: {install_agent_output.decode('utf-8')}"
        )

    def register_agent(self, app: docker.models.containers.Container, hostname: str) -> None:
        """Register an agent in an application container with a site."""
        cmd = [
            "/usr/bin/cmk-agent-ctl",
            "register",
            "--server",
            f"{self.ip}:{self.agent_receiver_port}",
            "--site",
            self.site_id,
            "--user",
            self.api_user,
            "--password",
            self.api_secret,
            "--hostname",
            hostname,
            "--trust-cert",
        ]
        logger.info("Running command: %s", " ".join(cmd))
        register_agent_rc, register_agent_output = app.exec_run(
            cmd,
            user="root",
        )
        assert register_agent_rc == 0, (
            f"Error registering agent: {register_agent_output.decode('utf-8')}"
        )

    @staticmethod
    def install_agent_controller_daemon(app: docker.models.containers.Container) -> None:
        """Install an agent controller daemon in an application container
        to avoid systemd dependency."""
        daemon_path = str(repo_path() / "tests" / "scripts" / "agent_controller_daemon.py")

        python_pkg_name = "python3.12"
        python_bin_name = "python3.12"
        logger.info("Installing %s...", python_pkg_name)
        install_python_rc, install_python_output = app.exec_run(
            f"dnf install '{python_pkg_name}'",
            user="root",
        )
        assert install_python_rc == 0, (
            f"Error during {python_pkg_name} setup: {install_python_output.decode('utf-8')}"
        )

        logger.info('Installing Checkmk agent controller daemon "%s"...', daemon_path)
        assert copy_to_container(app, daemon_path, "/")
        app.exec_run(
            f'{python_bin_name} "/{os.path.basename(daemon_path)}"',
            user="root",
            detach=True,
        )
