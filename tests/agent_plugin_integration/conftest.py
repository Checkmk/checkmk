#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import logging
import os
from collections.abc import Iterator
from pathlib import Path
from random import randint
from typing import Final

import docker
import docker.client
import docker.errors
import docker.models
import docker.models.containers
import docker.models.images
import pytest

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.docker import (
    copy_to_container,
    get_container_ip,
    resolve_image_alias,
)

logger = logging.getLogger()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--mk-oracle-binary-path",
        required=True,
        help="Path to a pre-built mk-oracle binary.",
    )


@pytest.fixture(name="mk_oracle_binary_path", scope="session")
def _mk_oracle_binary_path(request: pytest.FixtureRequest) -> Path:
    value: str = request.config.getoption("--mk-oracle-binary-path")
    return Path(value)


@pytest.fixture(name="client", scope="session")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="tmp_path_session", scope="session")
def _tmp_path_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("agent_plugin_integration")


class OracleDatabase:
    def __init__(
        self,
        client: docker.client.DockerClient,
        *,  # enforce named arguments
        temp_dir: Path,
        mk_oracle_binary_path: Path,
        name: str = "oracle",
    ):
        self.client = client
        self.container: docker.models.containers.Container
        self.name: str = name
        self.temp_dir = temp_dir

        self.IMAGE_NAME: Final[str] = "IMAGE_ORACLE_DB_23C"
        self.image = self._pull_image()
        # get predefined image environment
        self.default_environment = dict(
            [str(_).split("=", 1) for _ in self.image.attrs["Config"]["Env"]]
        )
        home_var = "ORACLE_HOME"
        assert home_var in self.default_environment, f"${home_var} is not defined in image!"
        self.ORACLE_HOME: Final[Path] = Path(self.default_environment[home_var])
        self.INIT_ORA: Final[Path] = self.ORACLE_HOME / "dbs" / "init.ora"
        self.SID: Final[str] = "FREE"  # Cannot be changed in FREE edition!
        self.PDB: Final[str] = "FREEPDB1"  # Cannot be changed in FREE edition!
        self.SERVICE_PREFIX: Final[str] = "ORA FREE"  # Cannot be changed in FREE edition!
        self.PORT: Final[int] = 1521

        self.tns_admin_dir = self.ORACLE_HOME / "network" / "admin"
        self.password = "oracle"
        self.sys_user_auth: str = f"sys/{self.password}@localhost:{self.PORT}/{self.SID}"
        self.charset = "AL32UTF8"
        self.wallet_dir = Path("/home/oracle/oracle_wallet")
        self.wallet_password = "wallywallet42"

        # database root folder
        self.ROOT: Final[Path] = Path("/opt/oracle")  # Cannot be changed!
        # database file folder within container
        self.DATA: Final[Path] = self.ROOT / "oradata"  # Cannot be changed!
        # external file system folder for environment file storage
        self.ORAENV: Final[Path] = (
            Path(os.environ["CMK_ORAENV"]) if "CMK_ORAENV" in os.environ else self.temp_dir
        )
        # external file system folder for database file storage (unset => use container)
        self.ORADATA: Final[Path | None] = (
            Path(os.environ["CMK_ORADATA"]) if "CMK_ORADATA" in os.environ else None
        )

        self.cmk_cfg_dir = Path("/etc/check_mk")
        self.cmk_var_dir = Path("/var/lib/check_mk_agent")
        self.cmk_plugin_dir = Path("/usr/lib/check_mk_agent/plugins")
        self.cmk_plugin = self.cmk_plugin_dir / "mk_oracle"
        # user name; use "c##<name>" notation for pluggable databases
        self.cmk_username: str = "c##checkmk"
        self.cmk_password: str = "cmk"
        self.cmk_credentials_cfg = self.cmk_cfg_dir / "mk_oracle.credentials.cfg"
        self.cmk_wallet_cfg = self.cmk_cfg_dir / "mk_oracle.wallet.cfg"
        self.cmk_cfg = self.cmk_cfg_dir / "mk_oracle.cfg"

        # New mk-oracle plugin
        self.new_plugin_binary_path: Path = mk_oracle_binary_path
        self.new_plugin_binary_name: Final[str] = self.new_plugin_binary_path.name
        self.new_plugin_dir: Final[Path] = self.cmk_plugin_dir / "packages" / "mk-oracle"
        self.new_plugin: Final[Path] = self.new_plugin_dir / self.new_plugin_binary_name
        self.new_plugin_cfg: Final[Path] = self.cmk_cfg_dir / "mk-oracle.yml"
        self.new_plugin_credentials_cfg: Final[Path] = (
            self.cmk_cfg_dir / "mk-oracle.credentials.yml"
        )
        self.new_plugin_wallet_cfg: Final[Path] = self.cmk_cfg_dir / "mk-oracle.wallet.yml"

        self.environment = {
            "ORACLE_SID": self.SID,
            "ORACLE_PDB": self.PDB,
            "ORACLE_PWD": self.password,
            "ORACLE_PASSWORD": self.password,
            "ORACLE_CHARACTERSET": self.charset,
            "MK_CONFDIR": self.cmk_cfg_dir.as_posix(),
            "MK_VARDIR": self.cmk_var_dir.as_posix(),
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
            "show_user.sql": "SHOW USER;",
            "register_listener.sql": "ALTER SYSTEM REGISTER;",
            "shutdown.sql": "shutdown immediate;exit;",
        }
        self.cfg_files = {
            self.cmk_credentials_cfg.name: "\n".join(
                [
                    "MAX_TASKS=10",
                    f"DBUSER='{self.cmk_username}:{self.cmk_password}::localhost:{self.PORT}:{self.SID}'",
                ]
            ),
            self.cmk_wallet_cfg.name: "\n".join(
                [
                    "MAX_TASKS=10",
                    "DBUSER='/:'",
                ]
            ),
        }
        self.volumes: list[str] = []

        # CMK_ORADATA can be specified for (re-)using a local, pluggable database folder
        # be default, a temporary database is created in the container
        if self.ORADATA:
            # ORADATA must be writeable to UID 54321
            os.makedirs(self.ORADATA, mode=0o777, exist_ok=True)
            self.volumes.append(f"{self.ORADATA.as_posix()}:{self.DATA.as_posix()}")

        self._init_envfiles()
        self._start_container()
        self._setup_container()

    @property
    def logs(self) -> str:
        return self.container.logs().decode("utf-8")

    def _create_oracle_wallet(self) -> None:
        logger.info("Creating Oracle wallet...")
        wallet_password = f"{self.wallet_password}\n{self.wallet_password}"
        cmd = ["mkstore", "-wrl", self.wallet_dir.as_posix(), "-create"]
        rc, output = self.container.exec_run(
            f"""bash -c 'echo -e "{wallet_password}" | {" ".join(cmd)}'""", user="oracle"
        )
        assert rc == 0, f"Error during wallet creation: {output.decode('UTF-8')}"
        logger.info("Creating Oracle wallet credential...")
        cmd = [
            "mkstore",
            "-wrl",
            self.wallet_dir.as_posix(),
            "-createCredential",
            f"{self.SID} {self.cmk_username} {self.cmk_password}",
        ]
        rc, output = self.container.exec_run(
            f"""bash -c 'echo "{self.wallet_password}" | {" ".join(cmd)}'""", user="oracle"
        )
        assert rc == 0, f"Error during wallet credential creation: {output.decode('UTF-8')}"

    def _init_envfiles(self) -> None:
        """Write environment files.

        CMK_ORAENV can be specified for using a local, customized script folder
        NOTE: The folder is never mounted as a volume, but the files are copied
        to the containers ORADATA folder instead."""

        for name, content in (self.sql_files | self.cfg_files).items():
            if not os.path.exists(path := self.ORAENV / name):
                with open(path, "w", encoding="UTF-8") as oraenv_file:
                    oraenv_file.write(content)

    def _pull_image(self) -> docker.models.images.Image:
        """Pull the container image from the repository."""
        logger.info("Downloading Oracle Database Free docker image")

        return self.client.images.pull(resolve_image_alias(self.IMAGE_NAME))

    def _start_container(self) -> None:
        """Start the container."""
        try:
            self.container = self.client.containers.get(self.name)
            if os.getenv("REUSE") == "1":
                logger.info("Reusing existing container %s", self.container.short_id)
                self.container.start()
            else:
                logger.info("Removing existing container %s", self.container.short_id)
                self.container.remove(force=True)
                raise docker.errors.NotFound(self.name)
        except docker.errors.NotFound:
            logger.info("Starting container %s from image %s", self.name, self.image.short_id)
            assert self.image.id, "Image ID not defined!"
            self.container = self.client.containers.run(
                image=self.image.id,
                name=self.name,
                volumes=self.volumes,
                environment=self.environment,
                detach=True,
                user="oracle",
            )

            success_msg = "DATABASE IS READY TO USE!"
            failure_msg = "Database configuration failed."
            try:
                wait_until(
                    lambda: any(_ in self.logs for _ in (success_msg, failure_msg)),
                    timeout=1200,
                    interval=5,
                )
            except TimeoutError:
                logger.error(
                    "TIMEOUT while starting Oracle. Log output: %s",
                    self.logs,
                )
                raise
            if failure_msg in self.logs:
                logger.error("ERROR while starting Oracle. Log output: %s", self.logs)
        # reload() to make sure all attributes are set (e.g. NetworkSettings)
        self.container.reload()
        self.ip = get_container_ip(self.container)

    def _setup_container(self) -> None:
        """Initialise the container setup."""

        logger.info("Unset the ociregion to prevent package management errors")
        self.container.exec_run("""bash -c 'echo ""> "/etc/yum/vars/ociregion"'""", user="root")

        logger.info("Copying environment files to container...")
        for name in self.sql_files:
            assert copy_to_container(self.container, self.ORAENV / name, self.ROOT), (
                "Failed to copy environment files!"
            )

        logger.info("Setup TNS listener")
        listener_ora_text = (
            "SID_LIST_LISTENER=(SID_LIST=(SID_DESC=(GLOBAL_DBNAME=FREE)(SID_NAME=FREE)))"
        )
        listener_ora = self.tns_admin_dir / "listener.ora"
        self.container.exec_run(
            f"""bash -c 'echo -e "{listener_ora_text}" >> "{listener_ora.as_posix()}"'"""
        )

        logger.info("Restart TNS listener")
        rc, output = self.container.exec_run("lsnrctl stop", user="oracle")
        assert rc == 0, f"Failed to stop listener: {output.decode('UTF-8')}"
        rc, output = self.container.exec_run("lsnrctl start", user="oracle")
        assert rc == 0, f"Failed to start listener: {output.decode('UTF-8')}"

        logger.info("Forcing listener registration...")
        rc, output = self.container.exec_run(
            f"""bash -c 'sqlplus -s "/ as sysdba" < "{self.ROOT}/register_listener.sql"'""",
            user="oracle",
        )
        assert rc == 0, f"Error during listener registration: {output.decode('UTF-8')}"

        logger.info('Creating Checkmk user "%s"...', self.cmk_username)
        rc, output = self.container.exec_run(
            f"""bash -c 'sqlplus -s "/ as sysdba" < "{self.ROOT}/create_user.sql"'""",
            user="oracle",
        )
        assert rc == 0, f"Error during user creation: {output.decode('UTF-8')}"

        login = f"{self.cmk_username}/{self.cmk_password}@{self.SID}"
        logger.info('Testing login "%s"...', login)
        rc, output = self.container.exec_run(
            f"""bash -c 'sqlplus -s "{login}" < "{self.ROOT}/show_user.sql"'""",
            user="oracle",
        )
        assert f"{self.cmk_username}" in output.decode("UTF-8").lower(), (
            f"Error while checking user: {output.decode('UTF-8')}"
        )

        self._install_oracle_plugin()
        self._install_new_oracle_plugin()
        self._create_oracle_wallet()

        logger.info(self.container.logs().decode("utf-8").strip())

    def _install_oracle_plugin(self) -> None:
        plugin_source_path = repo_path() / "agents" / "plugins" / self.cmk_plugin.name
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
        plugin_temp_path = self.temp_dir / self.cmk_plugin.name
        with open(plugin_temp_path, "w", encoding="UTF-8") as plugin_file:
            plugin_file.write(plugin_script)

        logger.info('Creating agent plugin target folder "%s"...', self.cmk_plugin_dir)
        rc, output = self.container.exec_run(
            rf'mkdir -p "{self.cmk_plugin_dir.as_posix()}"', user="root"
        )
        assert rc == 0, f'Could not create folder "{self.cmk_plugin_dir}"! Reason: {output}'
        logger.info('Creating agent plugin configuration folder "%s"...', self.cmk_cfg_dir)
        rc, output = self.container.exec_run(
            rf'mkdir -p "{self.cmk_cfg_dir.as_posix()}"', user="root"
        )
        assert rc == 0, f'Could not create "{self.cmk_cfg_dir}"! Reason: {output}'

        logger.info('Installing Oracle plugin "%s" to "%s"...', plugin_source_path, self.cmk_plugin)
        assert copy_to_container(
            self.container, plugin_temp_path.as_posix(), self.cmk_plugin_dir
        ), "Failed to copy Oracle plugin!"
        logger.info('Setting ownership for Oracle plugin "%s"...', self.cmk_plugin)
        rc, output = self.container.exec_run(
            rf'chmod +x "{self.cmk_plugin.as_posix()}"', user="root"
        )
        assert rc == 0, f"Error while setting ownership: {output.decode('UTF-8')}"
        logger.info("Installing Oracle plugin configuration files...")
        for cfg_file in self.cfg_files:
            assert copy_to_container(self.container, self.ORAENV / cfg_file, self.cmk_cfg_dir)
        self.use_credentials()

        logger.info("Create a link to Perl...")
        rc, output = self.container.exec_run(
            r"""bash -c 'ln -s "${ORACLE_HOME}/perl/bin/perl" "/usr/bin/perl"'""", user="root"
        )
        assert rc == 0, f"Error while creating a link to Perl: {output.decode('UTF-8')}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if is_cleanup_enabled():
            self.container.stop(timeout=30)
            self.container.remove(force=True)

    def use_credentials(self) -> None:
        logger.info("Enabling credential-based authentication...")
        with open(path := self.ORAENV / "sqlnet.ora", "w", encoding="UTF-8") as oraenv_file:
            oraenv_file.write("NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)")
        assert copy_to_container(self.container, path, self.tns_admin_dir), (
            f'Failed to copy "{path}"!'
        )
        rc, output = self.container.exec_run(
            rf'cp "{self.cmk_credentials_cfg.as_posix()}" "{self.cmk_cfg.as_posix()}"', user="root"
        )
        assert rc == 0, f"Failed to copy cfg file: {output.decode('UTF-8')}"

    def use_wallet(self) -> None:
        logger.info("Enabling wallet authentication...")
        with open(path := self.ORAENV / "sqlnet.ora", "w", encoding="UTF-8") as oraenv_file:
            oraenv_file.write(
                "\n".join(
                    [
                        "NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)",
                        "SQLNET.WALLET_OVERRIDE = TRUE",
                        "WALLET_LOCATION =",
                        "(SOURCE=",
                        "    (METHOD = FILE)",
                        f"    (METHOD_DATA = (DIRECTORY={self.wallet_dir.as_posix()}))",
                        ")",
                    ]
                )
            )
        assert copy_to_container(self.container, path, self.tns_admin_dir), (
            f'Failed to copy "{path}"!'
        )
        rc, output = self.container.exec_run(
            rf'cp "{self.cmk_wallet_cfg.as_posix()}" "{self.cmk_cfg.as_posix()}"', user="root"
        )
        assert rc == 0, f"Failed to copy cfg file: {output.decode('UTF-8')}"

    def _new_plugin_credentials_yml(self) -> str:
        return "\n".join(
            [
                "---",
                "oracle:",
                "  main:",
                "    connection:",
                "      hostname: localhost",
                f"      port: {self.PORT}",
                "    authentication:",
                f"      username: {self.cmk_username}",
                f"      password: {self.cmk_password}",
                "      type: standard",
                "    discovery:",
                "      detect: no",
                "    instances:",
                f"      - service_name: {self.SID}",
            ]
        )

    def _new_plugin_wallet_yml(self) -> str:
        return "\n".join(
            [
                "---",
                "oracle:",
                "  main:",
                "    connection:",
                "      hostname: localhost",
                f"      port: {self.PORT}",
                f"      tns_admin: {self.tns_admin_dir.as_posix()}",
                "    authentication:",
                "      type: wallet",
                "    discovery:",
                "      detect: no",
                "    instances:",
                f"      - alias: {self.SID}",
            ]
        )

    def _install_new_oracle_plugin(self) -> None:
        """Install the mk-oracle (Rust) plugin binary and config templates to the container."""

        logger.info('Creating new plugin target folder "%s"...', self.new_plugin_dir)
        rc, output = self.container.exec_run(
            rf'mkdir -p "{self.new_plugin_dir.as_posix()}"', user="root"
        )
        assert rc == 0, f'Could not create folder "{self.new_plugin_dir}"! Reason: {output}'

        logger.info(
            'Installing mk-oracle binary from "%s" to "%s"...',
            self.new_plugin_binary_path,
            self.new_plugin,
        )
        assert copy_to_container(
            self.container, str(self.new_plugin_binary_path), self.new_plugin_dir
        ), "Failed to copy mk-oracle binary!"
        rc, output = self.container.exec_run(
            rf'chmod +x "{self.new_plugin.as_posix()}"', user="root"
        )
        assert rc == 0, f"Error while setting executable bit: {output.decode('UTF-8')}"

        logger.info("Installing mk-oracle plugin configuration templates...")
        for name, content in {
            self.new_plugin_credentials_cfg.name: self._new_plugin_credentials_yml(),
            self.new_plugin_wallet_cfg.name: self._new_plugin_wallet_yml(),
        }.items():
            path = self.ORAENV / name
            if not os.path.exists(path):
                with open(path, "w", encoding="UTF-8") as cfg_file:
                    cfg_file.write(content)
            assert copy_to_container(self.container, path, self.cmk_cfg_dir), (
                f'Failed to copy "{name}"!'
            )

        self.use_new_plugin_credentials()

    def use_new_plugin_credentials(self) -> None:
        logger.info("Enabling credential-based authentication for mk-oracle...")
        with open(path := self.ORAENV / "sqlnet.ora", "w", encoding="UTF-8") as oraenv_file:
            oraenv_file.write("NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)")
        assert copy_to_container(self.container, path, self.tns_admin_dir), (
            f'Failed to copy "{path}"!'
        )
        rc, output = self.container.exec_run(
            rf'cp "{self.new_plugin_credentials_cfg.as_posix()}" "{self.new_plugin_cfg.as_posix()}"',
            user="root",
        )
        assert rc == 0, f"Failed to copy cfg file: {output.decode('UTF-8')}"

    def use_new_plugin_wallet(self) -> None:
        logger.info("Enabling wallet authentication for mk-oracle...")
        with open(path := self.ORAENV / "sqlnet.ora", "w", encoding="UTF-8") as oraenv_file:
            oraenv_file.write(
                "\n".join(
                    [
                        "NAMES.DIRECTORY_PATH= (TNSNAMES, EZCONNECT)",
                        "SQLNET.WALLET_OVERRIDE = TRUE",
                        "WALLET_LOCATION =",
                        "(SOURCE=",
                        "    (METHOD = FILE)",
                        f"    (METHOD_DATA = (DIRECTORY={self.wallet_dir.as_posix()}))",
                        ")",
                    ]
                )
            )
        assert copy_to_container(self.container, path, self.tns_admin_dir), (
            f'Failed to copy "{path}"!'
        )
        rc, output = self.container.exec_run(
            rf'cp "{self.new_plugin_wallet_cfg.as_posix()}" "{self.new_plugin_cfg.as_posix()}"',
            user="root",
        )
        assert rc == 0, f"Failed to copy cfg file: {output.decode('UTF-8')}"


@pytest.fixture(name="oracle", scope="session")
def _oracle(
    client: docker.client.DockerClient,
    tmp_path_session: Path,
    mk_oracle_binary_path: Path,
) -> Iterator[OracleDatabase]:
    with OracleDatabase(
        client,
        name=f"oracle_{randint(10000000, 99999999)}",
        temp_dir=tmp_path_session,
        mk_oracle_binary_path=mk_oracle_binary_path,
    ) as oracle_db:
        yield oracle_db
