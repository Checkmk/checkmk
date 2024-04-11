#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import docker  # type: ignore[import-untyped]
import pytest

from tests.testlib import repo_path
from tests.testlib.docker import (
    checkmk_docker_add_host,
    checkmk_docker_api_request,
    checkmk_docker_automation_secret,
    checkmk_docker_wait_for_services,
    checkmk_install_agent,
    checkmk_install_agent_controller_daemon,
    checkmk_register_agent,
    copy_to_container,
    get_container_ip,
    resolve_image_alias,
)

logger = logging.getLogger()


class OracleDatabase:

    def __init__(
        self,
        docker_client: docker.DockerClient,
        checkmk: docker.models.containers.Container,
        name: str = "oracle",
        temp_dir: Path = Path("/tmp"),
    ):
        self.docker_client = docker_client
        self.checkmk = checkmk
        self.name: str = name
        self.temp_dir = temp_dir

        self.IMAGE: Final[str] = "IMAGE_ORACLE_DB_23C"
        self.SID: Final[str] = "FREE"  # Cannot be changed for FREE edition docker image!
        self.PDB: Final[str] = "FREEPDB1"  # Cannot be changed for FREE edition docker image!
        self.PWD: Final[str] = "oracle"
        self.CHARSET: Final[str] = "AL32UTF8"
        self.PREFIX: Final[str] = "ORA FREE"  # Service prefix
        # user name; use "c##<name>" notation for pluggable databases
        self.USER: Final[str] = "c##checkmk"
        self.PASS: Final[str] = "cmk"
        self.PORT: Final[int] = 1521
        self.SYS_AUTH: Final[str] = f"sys/{self.PWD}@localhost:{self.PORT}/{self.SID}"

        # database root folder
        self.ROOT: Final[str] = "/opt/oracle"
        # database file folder within container
        self.DATA: Final[str] = "/opt/oracle/oradata"

        self.INIT_CMD: Final[str] = "/etc/rc.d/init.d/oracle-free-23c"

        # external file system folder for environment file storage
        self.ORAENV: Final[str] = os.getenv("CMK_ORAENV", self.temp_dir.as_posix())
        # external file system folder for database file storage (unset => use container)
        self.ORADATA: Final[str] = os.getenv("CMK_ORADATA", "")

        self.reuse_db = self.ORADATA and os.path.exists(f"{self.ORADATA}/{self.SID}")

        self.environment = {
            "ORACLE_SID": self.SID,
            "ORACLE_PDB": self.PDB,
            "ORACLE_PWD": self.PWD,
            "ORACLE_PASSWORD": self.PWD,
            "ORACLE_CHARACTERSET": self.CHARSET,
            "MK_CONFDIR": "/etc/check_mk",
            "MK_VARDIR": "/var/lib/check_mk_agent",
        }

        self.files = {
            "create_user.sql": "\n".join(
                [
                    f"CREATE USER IF NOT EXISTS {self.USER} IDENTIFIED BY {self.PASS};",
                    f"ALTER USER {self.USER} SET container_data=all container=current;",
                    f"GRANT select_catalog_role TO {self.USER} container=all;",
                    f"GRANT create session TO {self.USER} container=all;",
                ]
            ),
            "register_listener.sql": "ALTER SYSTEM REGISTER;",
            "mk_oracle.cfg": "\n".join(
                [
                    "MAX_TASKS=10",
                    f"DBUSER='{self.USER}:{self.PASS}::localhost:1521:{self.SID}'",
                ]
            ),
        }

        self.volumes = []

        # CMK_ORADATA can be specified for (re-)using a local, pluggable database folder
        # be default, a temporary database is created in the container
        if self.ORADATA:
            # ORADATA must be writeable to UID 54321
            os.makedirs(self.ORADATA, mode=0o777, exist_ok=True)
            self.volumes.append(f"{self.ORADATA}:{self.DATA}")

        self._init_envfiles()
        self.image = self._pull_image()
        self.container = self._start_container()
        self._setup_container()

    def _init_envfiles(self) -> None:
        """Write environment files.

        CMK_ORAENV can be specified for using a local, customized script folder
        NOTE: The folder is never mounted as a volume, but the files are copied
        to the containers ORADATA folder instead."""

        for name, content in self.files.items():
            if not os.path.exists(path := f"{self.ORAENV}/{name}"):
                with open(path, "w", encoding="UTF-8") as oraenv_file:
                    oraenv_file.write(content)

    def _pull_image(self) -> docker.models.images.Image:
        """Pull the container image from the repository."""
        logger.info("Downloading Oracle Database Free docker image")

        return self.docker_client.images.pull(resolve_image_alias(self.IMAGE))

    def _start_container(self) -> docker.models.containers.Container:
        """Start the container."""
        try:
            container = self.docker_client.containers.get(self.name)
            if os.getenv("REUSE") == "1":
                logger.info("Reusing existing container %s", container.short_id)
                container.start()
            else:
                logger.info("Removing existing container %s", container.short_id)
                container.remove(force=True)
                raise docker.errors.NotFound(self.name)
        except docker.errors.NotFound:
            logger.info("Starting container %s from image %s", self.name, self.image.short_id)
            container = self.docker_client.containers.run(
                image=self.image.id,
                name=self.name,
                volumes=self.volumes,
                environment=self.environment,
                detach=True,
                shm_size="4G",
                mem_limit="6G",
                memswap_limit="8G",
            )
        return container

    def _setup_container(self) -> None:
        """Initialise the container setup."""
        logger.info("Copying environment files to container...")
        for name in self.files:
            assert copy_to_container(
                self.container, f"{self.ORAENV}/{name}", self.ROOT
            ), "Failed to copy environment files!"

        if not self.reuse_db:
            for command, msg in {
                f"{self.INIT_CMD} start": "Starting Oracle database...",
                f"{self.INIT_CMD} delete": "Dropping Oracle database...",
                f"""/usr/bin/bash -c 'rm -rf "{self.DATA}/{self.SID}"'""": "Cleanup Oracle database...",
                f"{self.INIT_CMD} configure": "Creating new Oracle database...",
            }.items():
                logger.info(msg)
                print("=" * 80)
                print(f"$ {command} #{msg}")
                _, output = self.container.exec_run(
                    command, environment=self.environment, user="root", privileged=True, stream=True
                )
                for chunk in output:
                    print(chunk.decode("UTF-8").strip())
                print("=" * 80)

        logger.info("Forcing listener registration...")
        rc, _ = self.container.exec_run(
            f"""bash -c 'sqlplus -s "/ as sysdba" < "{self.ROOT}/register_listener.sql"'"""
        )
        assert rc == 0, "Error during listener registration!"

        logger.info('Creating Checkmk user "%s"...', self.USER)
        rc, _ = self.container.exec_run(
            f"""bash -c 'sqlplus -s "/ as sysdba" < "{self.ROOT}/create_user.sql"'"""
        )
        assert rc == 0, "Error during user creation!"

        # reload() to make sure all attributes are set (e.g. NetworkSettings)
        self.container.reload()

        site_ip = get_container_ip(self.checkmk)
        assert site_ip and site_ip != "127.0.0.1", "Failed to detect IP of checkmk container!"

        checkmk_install_agent(app=self.container, checkmk=self.checkmk)

        checkmk_install_agent_controller_daemon(app=self.container)

        self._install_oracle_plugin()

        checkmk_docker_add_host(
            checkmk=self.checkmk,
            hostname=self.name,
            ipv4=get_container_ip(self.container),
        )

        site_id = "cmk"
        api_user = "automation"
        api_secret = checkmk_docker_automation_secret(self.checkmk, site_id, api_user)
        checkmk_register_agent(
            self.container,
            site_ip=site_ip,
            site_id=site_id,
            hostname=self.name,
            api_user=api_user,
            api_secret=api_secret,
        )

        checkmk_docker_wait_for_services(checkmk=self.checkmk, hostname=self.name, min_services=5)

        logger.info(self.container.logs().decode("utf-8").strip())

    def _install_oracle_plugin(self) -> None:
        plugin_source_path = repo_path() / "agents" / "plugins" / "mk_oracle"
        plugin_target_folder = "/usr/lib/check_mk_agent/plugins"

        logger.info(
            "Patching the Oracle plugin: Detect free edition + Use default TNS_ADMIN path..."
        )
        with open(plugin_source_path, encoding="UTF-8") as plugin_file:
            plugin_script = plugin_file.read()
        # detect free edition
        plugin_script = plugin_script.replace(r"_pmon_'", r"_pmon_|^db_pmon_'")
        # use default TNS_ADMIN path
        plugin_script = plugin_script.replace(
            r"TNS_ADMIN=${TNS_ADMIN:-$MK_CONFDIR}",
            r"TNS_ADMIN=${TNS_ADMIN:-${ORACLE_HOME}/network/admin}",
        )
        plugin_temp_path = self.temp_dir / "mk_oracle"
        with open(plugin_temp_path, "w", encoding="UTF-8") as plugin_file:
            plugin_file.write(plugin_script)

        logger.info('Installing Oracle plugin "%s"...', plugin_source_path)
        assert copy_to_container(self.container, f"{self.ORAENV}/mk_oracle.cfg", "/etc/check_mk")
        assert copy_to_container(self.container, plugin_temp_path.as_posix(), plugin_target_folder)

        self.container.exec_run(
            rf'chmod +x "{plugin_target_folder}/mk_oracle"', user="root", privileged=True
        )
        logger.info("Create a link to Perl...")
        self.container.exec_run(
            r"""bash -c 'ln -s "${ORACLE_HOME}/perl/bin/perl" "/usr/bin/perl"'""",
            user="root",
            privileged=True,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if os.getenv("CLEANUP", "1") == "1":
            self.container.stop(timeout=30)
            self.container.remove(force=True)


@pytest.fixture(name="oracle", scope="session")
def _oracle(
    client: docker.DockerClient,
    checkmk: docker.models.containers.Container,
    tmp_path_session: Path,
) -> Iterator[OracleDatabase]:
    yield OracleDatabase(
        client,
        checkmk,
        name="oracle",
        temp_dir=tmp_path_session,
    )


def test_docker_oracle(
    checkmk: docker.models.containers.Container,
    oracle: OracleDatabase,
) -> None:
    expected_services = [
        {"state": 0} | _
        for _ in [
            {"description": f"{oracle.PREFIX}.CDB$ROOT Locks"},
            {"description": f"{oracle.PREFIX}.CDB$ROOT Long Active Sessions"},
            {"description": f"{oracle.PREFIX}.CDB$ROOT Performance"},
            {"description": f"{oracle.PREFIX}.CDB$ROOT Sessions"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Instance"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Locks"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Long Active Sessions"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Performance"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Recovery Status"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Sessions"},
            {"description": f"{oracle.PREFIX}.{oracle.PDB} Uptime"},
            {"description": f"{oracle.PREFIX} Instance"},
            {"description": f"{oracle.PREFIX} Locks"},
            {"description": f"{oracle.PREFIX} Logswitches"},
            {"description": f"{oracle.PREFIX} Long Active Sessions"},
            {"description": f"{oracle.PREFIX}.PDB$SEED Instance"},
            {"description": f"{oracle.PREFIX}.PDB$SEED Performance"},
            {"description": f"{oracle.PREFIX}.PDB$SEED Recovery Status"},
            {"description": f"{oracle.PREFIX}.PDB$SEED Uptime"},
            {"description": f"{oracle.PREFIX} Processes"},
            {"description": f"{oracle.PREFIX} Recovery Status"},
            {"description": f"{oracle.PREFIX} Sessions"},
            {"description": f"{oracle.PREFIX} Undo Retention"},
            {"description": f"{oracle.PREFIX} Uptime"},
        ]
    ]
    actual_services = [
        _.get("extensions")
        for _ in checkmk_docker_api_request(
            checkmk,
            "get",
            f"/objects/host/{oracle.name}/collections/services?columns=state&columns=description",
        ).json()["value"]
        if _.get("title").upper().startswith(oracle.PREFIX)
    ]

    missing_services = [
        f'{service.get("description")} (expected state: {service.get("state")}'
        for service in expected_services
        if service.get("description") not in [_.get("description") for _ in actual_services]
    ]
    assert len(missing_services) == 0, f"Missing services: {missing_services}"

    unexpected_services = [
        f'{service.get("description")} (actual state: {service.get("state")}'
        for service in actual_services
        if service.get("description") not in [_.get("description") for _ in expected_services]
    ]
    assert len(unexpected_services) == 0, f"Unexpected services: {unexpected_services}"

    invalid_services = [
        f'{service.get("description")} ({expected_state=}; {actual_state=})'
        for service in actual_services
        if (actual_state := service.get("state"))
        != (
            expected_state := next(
                (
                    _.get("state", 0)
                    for _ in expected_services
                    if _.get("description") == service.get("description")
                ),
                0,
            )
        )
    ]
    assert len(invalid_services) == 0, f"Invalid services: {invalid_services}"
