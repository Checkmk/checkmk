#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Final, Literal

import docker.client  # type: ignore[import-untyped]
import docker.errors  # type: ignore[import-untyped]
import docker.models  # type: ignore[import-untyped]
import docker.models.containers  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
import pytest

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
from tests.testlib.pytest_helpers.marks import skip_if_not_enterprise_edition
from tests.testlib.repo import repo_path
from tests.testlib.utils import wait_until

logger = logging.getLogger()


class OracleDatabase:
    def __init__(
        self,
        docker_client: docker.client.DockerClient,
        checkmk: docker.models.containers.Container,
        *,  # enforce named arguments
        temp_dir: Path,
        name: str = "oracle",
    ):
        self.docker_client = docker_client
        self.checkmk = checkmk
        self.name: str = name
        self.temp_dir = temp_dir

        self.IMAGE_NAME: Final[str] = "IMAGE_ORACLE_DB_23C"
        self.image = self._pull_image()
        # get predefined image environment
        self.default_environment = dict(
            [str(_).split("=", 1) for _ in self.image.attrs["Config"]["Env"]]
        )
        self.ORACLE_HOME: Final[str] = self.default_environment.get("ORACLE_HOME", "")
        assert self.ORACLE_HOME, "ORACLE_HOME is not defined in image!"
        self.SID: Final[str] = "FREE"  # Cannot be changed in FREE edition!
        self.PDB: Final[str] = "FREEPDB1"  # Cannot be changed in FREE edition!
        self.SERVICE_PREFIX: Final[str] = "ORA FREE"  # Cannot be changed in FREE edition!
        self.PORT: Final[int] = 1521

        self.tns_admin_dir = f"{self.ORACLE_HOME}/network/admin"
        self.password: str = "oracle"
        self.sys_user_auth: str = f"sys/{self.password}@localhost:{self.PORT}/{self.SID}"
        self.charset: str = "AL32UTF8"
        self.wallet_dir: str = "/etc/check_mk/oracle_wallet"
        self.wallet_password: str = "wallywallet42"

        # database root folder
        self.ROOT: Final[str] = "/opt/oracle"  # Cannot be changed!
        # database file folder within container
        self.DATA: Final[str] = "/opt/oracle/oradata"  # Cannot be changed!
        # external file system folder for environment file storage
        self.ORAENV: Final[str] = os.getenv("CMK_ORAENV", self.temp_dir.as_posix())
        # external file system folder for database file storage (unset => use container)
        self.ORADATA: Final[str] = os.getenv("CMK_ORADATA", "")
        self.reuse_db = self.ORADATA and os.path.exists(f"{self.ORADATA}/{self.SID}")

        self.cmk_conf_dir: str = "/etc/check_mk"
        self.cmk_var_dir: str = "/var/lib/check_mk_agent"
        self.cmk_plugin_dir: str = "/usr/lib/check_mk_agent/plugins"
        # user name; use "c##<name>" notation for pluggable databases
        self.cmk_username: str = "c##checkmk"
        self.cmk_password: str = "cmk"
        self.cmk_credentials_cfg: str = "mk_oracle.credentials.cfg"
        self.cmk_wallet_cfg: str = "mk_oracle.wallet.cfg"
        self.cmk_cfg: str = "mk_oracle.cfg"

        self.environment = {
            "ORACLE_SID": self.SID,
            "ORACLE_PDB": self.PDB,
            "ORACLE_PWD": self.password,
            "ORACLE_PASSWORD": self.password,
            "ORACLE_CHARACTERSET": self.charset,
            "MK_CONFDIR": self.cmk_conf_dir,
            "MK_VARDIR": self.cmk_var_dir,
        }

        self.sql_files = {
            "create_user.sql": "\n".join(
                [
                    f"CREATE USER IF NOT EXISTS {self.cmk_username} IDENTIFIED BY {self.cmk_password};",
                    f"ALTER USER {self.cmk_username} SET container_data=all container=current;",
                    f"GRANT select_catalog_role TO {self.cmk_username} container=all;",
                    f"GRANT create session TO {self.cmk_username} container=all;",
                ]
            ),
            "register_listener.sql": "ALTER SYSTEM REGISTER;",
        }
        self.cfg_files = {
            self.cmk_credentials_cfg: "\n".join(
                [
                    "MAX_TASKS=10",
                    f"DBUSER='{self.cmk_username}:{self.cmk_password}::localhost:{self.PORT}:{self.SID}'",
                ]
            ),
            self.cmk_wallet_cfg: "\n".join(
                [
                    "MAX_TASKS=10",
                    "DBUSER='/:'",
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
        self.container = self._start_container()
        self._setup_container()

    def _create_oracle_wallet(self) -> None:
        logger.info("Creating Oracle wallet...")
        wallet_password = f"{self.wallet_password}\n{self.wallet_password}"
        cmd = ["mkstore", "-wrl", self.wallet_dir, "-create"]
        rc, output = self.container.exec_run(
            f"""bash -c 'echo -e "{wallet_password}" | {" ".join(cmd)}'""",
            user="root",
            privileged=True,
        )
        assert rc == 0, f"Error during wallet creation: {output.decode('UTF-8')}"
        logger.info("Creating Oracle wallet credential...")
        cmd = [
            "mkstore",
            "-wrl",
            self.wallet_dir,
            "-createCredential",
            f"localhost:{self.PORT}/{self.SID} {self.cmk_username} {self.cmk_password}",
        ]
        rc, output = self.container.exec_run(
            f"""bash -c 'echo "{self.wallet_password}" | {" ".join(cmd)}'""",
            user="root",
            privileged=True,
        )
        assert rc == 0, f"Error during wallet credential creation: {output.decode('UTF-8')}"

    def _init_envfiles(self) -> None:
        """Write environment files.

        CMK_ORAENV can be specified for using a local, customized script folder
        NOTE: The folder is never mounted as a volume, but the files are copied
        to the containers ORADATA folder instead."""

        for name, content in (self.sql_files | self.cfg_files).items():
            if not os.path.exists(path := f"{self.ORAENV}/{name}"):
                with open(path, "w", encoding="UTF-8") as oraenv_file:
                    oraenv_file.write(content)

    def _pull_image(self) -> docker.models.images.Image:
        """Pull the container image from the repository."""
        logger.info("Downloading Oracle Database Free docker image")

        return self.docker_client.images.pull(resolve_image_alias(self.IMAGE_NAME))

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
                command=(
                    None
                    if self.reuse_db
                    else [
                        "/bin/bash",
                        "-c",
                        f"rm -rf '{self.DATA}/'**; /opt/oracle/runOracle.sh",
                    ]
                ),
                image=self.image.id,
                name=self.name,
                volumes=self.volumes,
                environment=self.environment,
                detach=True,
                shm_size="4G",
                mem_reservation="6G",
                mem_limit="8G",
                memswap_limit="8G",
            )
            try:
                wait_until(
                    lambda: "DATABASE IS READY TO USE!" in container.logs().decode("utf-8"),
                    timeout=900,
                )
            except TimeoutError:
                logger.error(
                    "TIMEOUT while starting Oracle. Log output: %s",
                    container.logs().decode("utf-8"),
                )
                raise
        return container

    def _setup_container(self) -> None:
        """Initialise the container setup."""
        logger.info("Copying environment files to container...")
        for name in self.sql_files:
            assert copy_to_container(
                self.container, f"{self.ORAENV}/{name}", self.ROOT
            ), "Failed to copy environment files!"

        logger.info("Forcing listener registration...")
        rc, output = self.container.exec_run(
            f"""bash -c 'sqlplus -s "/ as sysdba" < "{self.ROOT}/register_listener.sql"'"""
        )
        assert rc == 0, f"Error during listener registration: {output.decode('UTF-8')}"

        logger.info('Creating Checkmk user "%s"...', self.cmk_username)
        rc, output = self.container.exec_run(
            f"""bash -c 'sqlplus -s "/ as sysdba" < "{self.ROOT}/create_user.sql"'"""
        )
        assert rc == 0, f"Error during user creation: {output.decode('UTF-8')}"

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

        self._create_oracle_wallet()

        logger.info(self.container.logs().decode("utf-8").strip())

    def _install_oracle_plugin(self) -> None:
        plugin_source_path = repo_path() / "agents" / "plugins" / "mk_oracle"
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
        assert copy_to_container(
            self.container, plugin_temp_path.as_posix(), self.cmk_plugin_dir
        ), "Failed to copy Oracle plugin!"
        logger.info('Set ownership for Oracle plugin "%s"...', plugin_source_path)
        rc, output = self.container.exec_run(
            rf'chmod +x "{self.cmk_plugin_dir}/mk_oracle"', user="root", privileged=True
        )
        assert rc == 0, f"Error while setting ownership: {output.decode('UTF-8')}"
        logger.info("Installing Oracle plugin configuration files...")
        for cfg_file in self.cfg_files:
            assert copy_to_container(self.container, f"{self.ORAENV}/{cfg_file}", self.cmk_conf_dir)
        self.use_credentials()

        logger.info("Create a link to Perl...")
        rc, output = self.container.exec_run(
            r"""bash -c 'ln -s "${ORACLE_HOME}/perl/bin/perl" "/usr/bin/perl"'""",
            user="root",
            privileged=True,
        )
        assert rc == 0, f"Error while creating a link to Perl: {output.decode('UTF-8')}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if os.getenv("CLEANUP", "1") == "1":
            self.container.stop(timeout=30)
            self.container.remove(force=True)

    def use_credentials(self) -> None:
        logger.info("Enabling credential-based authentication...")
        with open(path := f"{self.ORAENV}/sqlnet.ora", "w", encoding="UTF-8") as oraenv_file:
            oraenv_file.write("NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)")
        assert copy_to_container(
            self.container, path, self.tns_admin_dir
        ), f'Failed to copy "{path}"!'
        rc, output = self.container.exec_run(
            rf'cp "{self.cmk_conf_dir}/{self.cmk_credentials_cfg}" "{self.cmk_conf_dir}/{self.cmk_cfg}"',
            user="root",
            privileged=True,
        )
        assert rc == 0, f"Failed to copy cfg file: {output.decode('UTF-8')}"

    def use_wallet(self) -> None:
        logger.info("Enabling wallet authentication...")
        with open(path := f"{self.ORAENV}/sqlnet.ora", "w", encoding="UTF-8") as oraenv_file:
            oraenv_file.write(
                "\n".join(
                    [
                        "NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)",
                        "SQLNET.WALLET_OVERRIDE = TRUE",
                        "WALLET_LOCATION =",
                        "(SOURCE=",
                        "    (METHOD = FILE)",
                        f"    (METHOD_DATA = (DIRECTORY={self.wallet_dir}))",
                        ")",
                    ]
                )
            )
        assert copy_to_container(
            self.container, path, self.tns_admin_dir
        ), f'Failed to copy "{path}"!'
        rc, output = self.container.exec_run(
            rf'cp "{self.cmk_conf_dir}/{self.cmk_wallet_cfg}" "{self.cmk_conf_dir}/{self.cmk_cfg}"',
            user="root",
            privileged=True,
        )
        assert rc == 0, f"Failed to copy cfg file: {output.decode('UTF-8')}"


@pytest.fixture(name="oracle", scope="session")
def _oracle(
    client: docker.client.DockerClient,
    checkmk: docker.models.containers.Container,
    tmp_path_session: Path,
) -> Iterator[OracleDatabase]:
    with OracleDatabase(
        client,
        checkmk,
        name="oracle",
        temp_dir=tmp_path_session,
    ) as oracle_db:
        # Make use of the contextmanager logic to make sure that a teardown of
        # the database happens after the tests end.
        yield oracle_db


@skip_if_not_enterprise_edition
@pytest.mark.parametrize("auth_mode", ["wallet", "credential"])
def test_docker_oracle(
    checkmk: docker.models.containers.Container,
    oracle: OracleDatabase,
    auth_mode: Literal["wallet", "credential"],
) -> None:
    if auth_mode == "wallet":
        oracle.use_wallet()
    else:
        oracle.use_credentials()
    rc, output = oracle.container.exec_run(
        f"""bash -c '{oracle.cmk_plugin_dir}/mk_oracle -t'""",
        user="root",
        privileged=True,
    )
    assert rc == 0, (
        f"Oracle plugin could not connect to database using {auth_mode} authentication!\n"
        f"{output.decode('utf-8')}"
    )
    expected_services = [
        {"state": 0} | _
        for _ in [
            {"description": f"{oracle.SERVICE_PREFIX}.CDB$ROOT Locks"},
            {"description": f"{oracle.SERVICE_PREFIX}.CDB$ROOT Long Active Sessions"},
            {"description": f"{oracle.SERVICE_PREFIX}.CDB$ROOT Performance"},
            {"description": f"{oracle.SERVICE_PREFIX}.CDB$ROOT Sessions"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Instance"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Locks"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Long Active Sessions"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Performance"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Recovery Status"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Sessions"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB} Uptime"},
            {"description": f"{oracle.SERVICE_PREFIX} Instance"},
            {"description": f"{oracle.SERVICE_PREFIX} Locks"},
            {"description": f"{oracle.SERVICE_PREFIX} Logswitches"},
            {"description": f"{oracle.SERVICE_PREFIX} Long Active Sessions"},
            {"description": f"{oracle.SERVICE_PREFIX}.PDB$SEED Instance"},
            {"description": f"{oracle.SERVICE_PREFIX}.PDB$SEED Performance"},
            {"description": f"{oracle.SERVICE_PREFIX}.PDB$SEED Recovery Status"},
            {"description": f"{oracle.SERVICE_PREFIX}.PDB$SEED Uptime"},
            {"description": f"{oracle.SERVICE_PREFIX} Processes"},
            {"description": f"{oracle.SERVICE_PREFIX} Recovery Status"},
            {"description": f"{oracle.SERVICE_PREFIX} Sessions"},
            {"description": f"{oracle.SERVICE_PREFIX} Undo Retention"},
            {"description": f"{oracle.SERVICE_PREFIX} Uptime"},
        ]
    ]
    actual_services = [
        _.get("extensions")
        for _ in checkmk_docker_api_request(
            checkmk,
            "get",
            f"/objects/host/{oracle.name}/collections/services?columns=state&columns=description",
        ).json()["value"]
        if _.get("title").upper().startswith(oracle.SERVICE_PREFIX)
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
