#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io
import logging
import os
import subprocess
import tarfile
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, nullcontext, suppress
from pathlib import Path
from typing import Any, ContextManager

import docker  # type: ignore[import-untyped]
import docker.errors  # type: ignore[import-untyped]
import docker.models  # type: ignore[import-untyped]
import docker.models.containers  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
import requests

from tests.testlib.repo import repo_path
from tests.testlib.utils import wait_until
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger()

build_path = str(repo_path() / "docker_image")
image_prefix = "docker-tests"
distro_codename = "jammy"
cse_config_root = Path("/tmp/cmk-docker-test/cse-config-volume")


def cleanup_old_packages() -> None:
    """Cleanup files created by _prepare_package during previous job executions"""
    for p in Path(build_path).glob("*.deb"):
        logger.info("Cleaning up old package %s", p)
        p.unlink()


def copy_to_container(c: docker.models.containers.Container, source: str, target: str) -> bool:
    """Copy a source file to the target folder in the container."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w|") as tar, open(source, "rb") as f:
        info = tar.gettarinfo(fileobj=f)
        info.name = os.path.basename(source)
        tar.addfile(info, f)

    return bool(c.put_archive(target, stream.getvalue()))


def get_container_ip(c: docker.models.containers.Container) -> str:
    """Return the primary IP address for a given container name."""
    output = f"{c.attrs['NetworkSettings']['IPAddress']}" or "127.0.0.1"

    return output


def send_to_container(c: docker.models.containers.Container, text: str) -> None:
    """Send text to the STDIN of a given container."""
    s = c.attach_socket(params={"stdin": 1, "stream": 1})
    s._sock.send(text.encode("utf-8"))
    s.close()


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


def pull_checkmk(client: docker.DockerClient, version: CMKVersion) -> docker.models.images.Image:
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
        [
            os.path.join(repo_path(), "buildscripts/docker_image_aliases/resolve.py"),
            alias,
        ],
        text=True,
    ).split("\n", maxsplit=1)[0]


def build_checkmk(
    client: docker.DockerClient,
    version: CMKVersion,
    prepare_pkg: bool = True,
) -> tuple[docker.models.images.Image, Iterator[Mapping[str, Any]]]:
    prepare_build()

    if prepare_pkg:
        prepare_package(version)

    logger.info("Building docker image (or reuse existing): %s", image_name(version))
    try:
        image: docker.models.images.Image
        build_logs: Iterator[Mapping[str, Any]]
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
        "TZ=",
        "CMK_CONTAINERIZED=TRUE",
    ]

    assert "Healthcheck" in config

    assert config["Entrypoint"] == ["/docker-entrypoint.sh"]

    assert config["ExposedPorts"] == {
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


def _remove_volumes(
    client: docker.DockerClient, volumes: list[str] | None, is_update: bool
) -> None:
    """remove any pre-existing volumes"""
    volume_ids = [_.split(":")[0] for _ in volumes or []]
    exceptions: list[type[docker.errors.APIError]] = [docker.errors.NotFound]
    if is_update:
        exceptions.append(docker.errors.APIError)
    with suppress(*exceptions):
        for volume_id in volume_ids:
            client.volumes.get(volume_id).remove(force=True)


@contextmanager
def start_checkmk(
    client: docker.DockerClient,
    version: CMKVersion | None = None,
    is_update: bool = False,
    site_id: str = "cmk",
    name: str | None = None,
    hostname: str | None = None,
    environment: dict[str, str] | None = None,
    ports: dict[str, int | None | tuple[str, int] | list[int]] | None = None,
    volumes: list[str] | None = None,
    volumes_from: list[str] | None = None,
) -> Iterator[docker.models.containers.Container]:
    """Provide a readily configured Checkmk docker container."""
    environment = {"CMK_PASSWORD": "cmk"} | (environment or {})
    version = version or version_from_env()
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

    if version.is_saas_edition():
        from tests.testlib.cse.utils import (  # pylint: disable=import-error, no-name-in-module
            create_cse_initial_config,
        )

        create_cse_initial_config(root=Path(cse_config_root))
        volumes = (volumes or []) + get_cse_volumes(cse_config_root)
    volumes = volumes or None

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

    c: docker.models.containers.Container | None = None
    try:
        try:
            if not name:
                raise ValueError("Container name not defined!")
            c = client.containers.get(name)
            if os.getenv("REUSE") == "1":
                logger.info("Reusing existing container %s", c.short_id)
                c.start()
                c.exec_run(["omd", "start"], user=site_id)
            else:
                logger.info("Removing existing container %s", c.short_id)
                c.remove(force=True)
                _remove_volumes(client, volumes, is_update)
                raise docker.errors.NotFound(name)
        except (docker.errors.NotFound, docker.errors.NullResource, ValueError):
            assert (c := client.containers.run(image=_image, detach=True, **kwargs))
            logger.info("Starting container %s from image %s", c.short_id, _image.short_id)

            try:
                site_id = (environment).get("CMK_SITE_ID", site_id)
                wait_until(lambda: "### CONTAINER STARTED" in c.logs().decode("utf-8"), timeout=120)
                output = c.logs().decode("utf-8")

                assert ("Created new site" in output) != is_update
                assert ("cmkadmin with password:" in output) != is_update

                assert "STARTING SITE" in output
            except TimeoutError:
                logger.error(
                    "TIMEOUT while starting Checkmk. Log output: %s",
                    c.logs().decode("utf-8"),
                )
                raise

        status_rc, status_output = c.exec_run(["omd", "status"], user=site_id)
        assert status_rc == 0, f"Status is {status_rc}. Output: {status_output.decode('utf-8')}"

        # reload() to make sure all attributes are set (e.g. NetworkSettings)
        c.reload()

        logger.debug(c.logs().decode("utf-8"))

        cse_oauth_context_mngr: ContextManager = nullcontext()
        if version.is_saas_edition():
            from tests.testlib.cse.utils import (  # pylint: disable=import-error, no-name-in-module
                cse_openid_oauth_provider,
            )

            # TODO: The Oauth provider is currently not reachable from the Checkmk container.
            # To fix this, we should contenairize the Oauth provider as well and provide the Oauth
            # provider container IP address to the Checkmk container (via the cognito-cmk.json file).
            # This is similar to what we are doing with the Oracle container in the test_docker_oracle
            # test.
            cse_oauth_context_mngr = cse_openid_oauth_provider(
                site_url=f"http://{get_container_ip(c)}:5000", config_root=cse_config_root
            )

        with cse_oauth_context_mngr:
            yield c
    finally:
        if os.getenv("CLEANUP", "1") != "0" and c:
            c.stop()
            c.remove(v=True, force=True)


def get_cse_volumes(config_root: Path) -> list[str]:
    cse_config_dir = Path("etc/cse")
    cse_config_on_local_machine = config_root / cse_config_dir
    cse_config_on_container = Path("/") / cse_config_dir
    return [f"{cse_config_on_local_machine}:{cse_config_on_container}:ro"]


def checkmk_docker_automation_secret(
    checkmk: docker.models.containers.Container,
    site_id: str = "cmk",
    api_user: str = "automation",
) -> str:
    """Return the automation secret for a Checkmk docker instance."""
    secret_rc, secret_output = checkmk.exec_run(
        f"cat '/omd/sites/{site_id}/var/check_mk/web/{api_user}/automation.secret'"
    )
    assert secret_rc == 0

    api_secret = secret_output.decode("utf-8").split("\n")[0]
    assert api_secret

    return f"{api_secret}"


def checkmk_docker_api_request(
    checkmk: docker.models.containers.Container,
    method: str,
    endpoint: str,
    json: Any | None = None,
    allow_redirects: bool = True,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    """Run an API request against a Checkmk docker instance."""
    site_ip = get_container_ip(checkmk)
    # docker container defaults
    site_port = 5000
    site_id = "cmk"

    api_url = f"http://{site_ip}:{site_port}/{site_id}/check_mk/api/1.0/{endpoint}"
    api_user = "automation"
    api_secret = checkmk_docker_automation_secret(checkmk, site_id, api_user)
    api_token = f"Bearer {api_user} {api_secret}"
    api_headers = {
        "Authorization": api_token,
        "Content-Type": "application/json",
        "If-Match": "*",
    }
    if headers:
        api_headers.update(headers)
    return requests.request(
        method,
        url=f"{api_url}",
        headers=api_headers,
        json=json,
        allow_redirects=allow_redirects,
    )


def checkmk_docker_get_host_services(
    checkmk: docker.models.containers.Container,
    hostname: str,
) -> Any:
    """Return the service list for a host in a Checkmk docker instance."""
    return checkmk_docker_api_request(
        checkmk, "get", f"/objects/host/{hostname}/collections/services"
    ).json()["value"]


def checkmk_docker_activate_changes(
    checkmk: docker.models.containers.Container, attempts: int = 15
) -> bool:
    """Activate changes in a Checkmk docker instance and wait for completion."""
    activate_response = checkmk_docker_api_request(
        checkmk,
        "post",
        "/domain-types/activation_run/actions/activate-changes/invoke",
    )
    if activate_response.status_code == 204:
        return True

    # wait for completion
    activation_id = activate_response.json().get("id")
    for _ in range(attempts):
        if (
            checkmk_docker_api_request(
                checkmk,
                "get",
                f"/objects/activation_run/{activation_id}/actions/wait-for-completion/invoke",
            ).status_code
            == 204
        ):
            return True
        time.sleep(1)

    return False


def checkmk_docker_discover_services(
    checkmk: docker.models.containers.Container, hostname: str, attempts: int = 15
) -> bool:
    """Perform a service discovery within a Checkmk docker instance and wait for completion."""
    checkmk_docker_schedule_check(checkmk, hostname, "Check_MK")
    checkmk_docker_schedule_check(checkmk, hostname, "Check_MK Discovery")
    discovery_response = checkmk_docker_api_request(
        checkmk,
        "post",
        f"/objects/host/{hostname}/actions/discover_services/invoke",
        json={
            "mode": "tabula_rasa",
        },
    )
    if discovery_response.status_code == 204:
        return True

    # wait for completion
    for _ in range(attempts):
        if (
            checkmk_docker_api_request(
                checkmk,
                "get",
                f"/objects/service_discovery_run/{hostname}/actions/wait-for-completion/invoke",
            ).status_code
            == 204
        ):
            return True
        time.sleep(1)

    return False


def checkmk_docker_schedule_check(
    checkmk: docker.models.containers.Container,
    hostname: str,
    checkname: str = "Check_MK",
    site_id: str = "cmk",
) -> None:
    """Schedule a check for a host in a Checkmk docker instance."""
    cmd_time = time.time()
    checkmk.exec_run(
        [
            f"/omd/sites/{site_id}/bin/lq",
            f"COMMAND [{cmd_time}] SCHEDULE_FORCED_SVC_CHECK;{hostname};{checkname};{cmd_time}",
        ],
        user=site_id,
    )


def checkmk_docker_add_host(
    checkmk: docker.models.containers.Container,
    hostname: str,
    ipv4: str,
) -> None:
    """Create a host in a Checkmk docker instance."""
    checkmk_docker_api_request(
        checkmk,
        "post",
        "/domain-types/host_config/collections/all",
        json={
            "folder": "/",
            "host_name": hostname,
            "attributes": {
                "ipaddress": ipv4,
                "tag_address_family": "ip-v4-only",
            },
        },
    )
    checkmk_docker_activate_changes(checkmk)


def checkmk_docker_wait_for_services(
    checkmk: docker.models.containers.Container,
    hostname: str,
    min_services: int = 5,
    attempts: int = 15,
) -> None:
    """Repeatedly discover services in a Checkmk docker instance until min_services are found."""
    for _ in range(attempts):
        if len(checkmk_docker_get_host_services(checkmk, hostname)) > min_services:
            break

        checkmk_docker_discover_services(checkmk, hostname)
        checkmk_docker_activate_changes(checkmk)


def checkmk_install_agent(
    app: docker.models.containers.Container,
    checkmk: docker.models.containers.Container,
) -> None:
    """Download an agent from Checkmk container and install it into an application container."""
    agent_os = "linux"
    agent_type = "rpm"
    agent_path = f"/tmp/check_mk_agent.{agent_type}"

    logger.info('Downloading Checkmk agent "%s"...', agent_path)
    with open(agent_path, "wb") as agent_file:
        agent_file.write(
            checkmk_docker_api_request(
                checkmk,
                "get",
                f"/domain-types/agent/actions/download/invoke?os_type={agent_os}_{agent_type}",
            ).content
        )

    logger.info('Installing Checkmk agent "%s"...', agent_path)
    assert copy_to_container(app, agent_path, "/")
    install_agent_rc, install_agent_output = app.exec_run(
        f"dnf install '/{os.path.basename(agent_path)}'",
        user="root",
        privileged=True,
    )
    assert (
        install_agent_rc == 0
    ), f"Error during agent installation: {install_agent_output.decode('utf-8')}"

    logger.info("Installing mk_oracle.cfg")
    setup_agent_rc, setup_agent_output = app.exec_run(
        """bash -c 'cp -f "/opt/oracle/oraenv/mk_oracle.cfg" "/etc/check_mk/mk_oracle.cfg"'""",
        user="root",
        privileged=True,
    )
    assert setup_agent_rc == 0, f"Error during agent setup: {setup_agent_output.decode('utf-8')}"


def checkmk_register_agent(
    app: docker.models.containers.Container,
    site_ip: str,
    site_id: str,
    hostname: str,
    api_user: str,
    api_secret: str,
    agent_receiver_port: int = 8000,
) -> None:
    """Register an agent in an application container with a site."""
    cmd = [
        "/usr/bin/cmk-agent-ctl",
        "register",
        "--server",
        f"{site_ip}:{agent_receiver_port}",
        "--site",
        site_id,
        "--user",
        api_user,
        "--password",
        api_secret,
        "--hostname",
        hostname,
        "--trust-cert",
    ]
    logger.info("Running command: %s", " ".join(cmd))
    register_agent_rc, register_agent_output = app.exec_run(
        cmd,
        user="root",
        privileged=True,
    )
    assert (
        register_agent_rc == 0
    ), f"Error registering agent: {register_agent_output.decode('utf-8')}"


def checkmk_install_agent_controller_daemon(
    app: docker.models.containers.Container,
) -> None:
    """Install an agent controller daemon in an application container
    to avoid systemd dependency."""
    daemon_path = str(repo_path() / "tests" / "scripts" / "agent_controller_daemon.py")

    logger.info("Installing Python...")
    install_python_rc, install_python_output = app.exec_run(
        "dnf install 'python3.11'",
        user="root",
        privileged=True,
    )
    assert (
        install_python_rc == 0
    ), f"Error during python setup: {install_python_output.decode('utf-8')}"

    logger.info('Installing Checkmk agent controller daemon "%s"...', daemon_path)
    assert copy_to_container(app, daemon_path, "/")
    app.exec_run(
        f'python3 "/{os.path.basename(daemon_path)}"',
        user="root",
        privileged=True,
        detach=True,
    )
