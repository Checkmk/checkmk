#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import os
from collections.abc import Iterator
from pathlib import Path
from random import randint
from typing import Final, Literal

import docker.client  # type: ignore[import-untyped]
import docker.errors  # type: ignore[import-untyped]
import docker.models  # type: ignore[import-untyped]
import docker.models.containers  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
import pytest

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.docker import (
    CheckmkApp,
    copy_to_container,
    get_container_ip,
    resolve_image_alias,
)

logger = logging.getLogger()


class OracleDatabase:
    def __init__(
        self,
        client: docker.client.DockerClient,
        checkmk: CheckmkApp,
        *,  # enforce named arguments
        temp_dir: Path,
        name: str = "oracle",
    ):
        self.client = client
        self.container: docker.models.containers.Container
        self.checkmk = checkmk
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
        self._create_oracle_wallet()

        if self.checkmk is not None:
            site_ip = self.checkmk.ip
            assert site_ip and site_ip != "127.0.0.1", "Failed to detect IP of checkmk container!"
            self.checkmk.install_agent(app=self.container, agent_type="rpm")
            self.checkmk.install_agent_controller_daemon(app=self.container)
            self.checkmk.openapi.hosts.create(
                self.name,
                folder="/",
                attributes={
                    "ipaddress": self.ip,
                    "tag_address_family": "ip-v4-only",
                },
            )
            self.checkmk.openapi.changes.activate_and_wait_for_completion()

            # like tests.testlib.agent.register_controller(), but in the container
            self.checkmk.register_agent(self.container, self.name)

            logger.info("Waiting for controller to open TCP socket or push data")
            # like tests.testlib.agent.wait_until_host_receives_data(), but in the container
            cmk_dump_cmd = [
                "su",
                "-l",
                self.checkmk.site_id,
                "-c",
                f'"{self.checkmk.site_root}/bin/cmk" -d "{self.name}"',
            ]
            try:
                wait_until(
                    lambda: self.checkmk.container.exec_run(cmk_dump_cmd)[0] == 0,
                    timeout=300,
                    interval=20,
                )
            except TimeoutError as excp:
                cmk_dump_rc, cmk_dump_output = self.checkmk.container.exec_run(cmk_dump_cmd)
                logger.error(
                    '"%s" failed with rc=%s!\nOutput: %s',
                    " ".join(cmk_dump_cmd),
                    cmk_dump_rc,
                    cmk_dump_output,
                )
                raise excp

            self.checkmk.openapi.service_discovery.run_discovery_and_wait_for_completion(
                self.name, timeout=300
            )
            self.checkmk.openapi.changes.activate_and_wait_for_completion()

            min_service_count = 10
            logger.info(
                "Wait until host %s has at least %s non-pending ORACLE services...",
                self.name,
                min_service_count,
            )

            def _host_has_prefixed_services(host_name: str, prefix: str, min_count: int) -> bool:
                services = self.checkmk.openapi.services.get_host_services(
                    host_name,
                    columns=["description", "has_been_checked"],
                )
                prefixed_services = [
                    _ for _ in services if _["extensions"]["description"].upper().startswith(prefix)
                ]
                if len(prefixed_services) < min_count:
                    return False
                return all(True for _ in prefixed_services if _["extensions"]["has_been_checked"])

            wait_until(
                lambda: _host_has_prefixed_services(
                    self.name, self.SERVICE_PREFIX, min_service_count
                ),
                timeout=300,
                interval=60,
            )
            self.checkmk.openapi.changes.activate_and_wait_for_completion()

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

        if self.checkmk is None:
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
        if os.getenv("CLEANUP", "1") == "1":
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


@pytest.fixture(name="oracle", scope="session")
def _oracle(
    client: docker.client.DockerClient,
    checkmk: CheckmkApp,
    tmp_path_session: Path,
) -> Iterator[OracleDatabase]:
    with OracleDatabase(
        client,
        checkmk,
        name=f"oracle_for_{checkmk.name}"
        if checkmk is not None and checkmk.name
        else f"oracle_{randint(10000000, 99999999)}",
        temp_dir=tmp_path_session,
    ) as oracle_db:
        yield oracle_db


@pytest.mark.skip_if_not_edition("enterprise")
@pytest.mark.parametrize("auth_mode", ["wallet", "credential"])
def test_docker_oracle(
    checkmk: CheckmkApp,
    oracle: OracleDatabase,
    auth_mode: Literal["wallet", "credential"],
) -> None:
    if auth_mode == "wallet":
        oracle.use_wallet()
    else:
        oracle.use_credentials()
    rc, output = oracle.container.exec_run([oracle.cmk_plugin.as_posix(), "-t"], user="root")
    agent_plugin_output = output.decode("utf-8")
    assert rc == 0 and "test login works" in agent_plugin_output, (
        f"Oracle plugin could not connect to database using {auth_mode} authentication!\n"
        f"{agent_plugin_output}"
    )
    rc, output = oracle.container.exec_run(
        f"""bash -c '{oracle.cmk_plugin.as_posix()}'""", user="root"
    )
    agent_plugin_output = output.decode("utf-8")
    assert rc == 0, f"Oracle plugin failed!\n{agent_plugin_output}"

    raw_sections = [f"<<<{_.strip()}" for _ in agent_plugin_output.split("\n<<<")]
    section_headers = [_.split("\n", 1)[0].strip() for _ in raw_sections]
    empty_section_headers = [_.split("\n", 1)[0].strip() for _ in raw_sections if _.endswith(">>>")]
    non_empty_section_headers = [_ for _ in section_headers if _ not in empty_section_headers]
    actual_sections = list({_[3:-3].split(":", 1)[0] for _ in section_headers})
    actual_non_empty_sections = list({_[3:-3].split(":", 1)[0] for _ in non_empty_section_headers})

    expected_non_empty_sections = [
        "oracle_instance",
        "oracle_sessions",
        "oracle_logswitches",
        "oracle_undostat",
        "oracle_processes",
        "oracle_recovery_status",
        "oracle_longactivesessions",
        "oracle_performance",
        "oracle_locks",
        "oracle_systemparameter",
        "oracle_instance",
        "oracle_processes",
    ]
    expected_sections = expected_non_empty_sections + [
        "oracle_recovery_area",
        "oracle_dataguard_stats",
        "oracle_tablespaces",
        "oracle_rman",
        "oracle_jobs",
        "oracle_resumable",
        "oracle_iostats",
        "oracle_asm_diskgroup",
    ]

    missing_sections = [_ for _ in expected_sections if _ not in actual_sections]
    assert len(missing_sections) == 0, f"Missing sections from agent output: {missing_sections}"

    missing_non_empty_sections = [
        _ for _ in expected_non_empty_sections if _ not in actual_non_empty_sections
    ]
    assert len(missing_non_empty_sections) == 0, (
        f"Missing non-empty sections from agent output: {missing_non_empty_sections}"
    )

    if checkmk is None:
        return

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
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB}.TEMP Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB}.SYSTEM Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB}.SYSAUX Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB}.UNDOTBS1 Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.{oracle.PDB}.USERS Tablespace"},
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
            {"description": f"{oracle.SERVICE_PREFIX}.CDB$ROOT.TEMP Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.UNDOTBS1 Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.SYSAUX Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.SYSTEM Tablespace"},
            {"description": f"{oracle.SERVICE_PREFIX}.USERS Tablespace"},
        ]
    ]

    actual_services = [
        _["extensions"]
        for _ in checkmk.openapi.services.get_host_services(
            oracle.name, columns=["state", "description"]
        )
        if _["extensions"]["description"].upper().startswith(oracle.SERVICE_PREFIX)
        and not _["extensions"]["description"].upper().endswith(" JOB")
    ]

    missing_services = [
        service["description"]
        for service in expected_services
        if service.get("description") not in [_.get("description") for _ in actual_services]
    ]
    assert len(missing_services) == 0, f"Missing services: {missing_services}"

    unexpected_services = [
        service.get("description")
        for service in actual_services
        if service.get("description") not in [_.get("description") for _ in expected_services]
    ]
    assert len(unexpected_services) == 0, f"Unexpected services: {unexpected_services}"

    invalid_services = [
        f"{service.get('description')} ({expected_state=}; {actual_state=})"
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
