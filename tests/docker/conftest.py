#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import docker  # type: ignore[import-untyped]
import pytest

from tests.testlib.docker import (
    checkmk_docker_add_host,
    checkmk_docker_automation_secret,
    checkmk_docker_wait_for_services,
    checkmk_install_agent,
    checkmk_install_agent_controller_daemon,
    checkmk_register_agent,
    copy_to_container,
    get_container_ip,
    resolve_image_alias,
    start_checkmk,
)
from tests.testlib.repo import repo_path
from tests.testlib.utils import execute, makedirs, wait_until, write_file
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger()


@pytest.fixture(scope="session")
def version() -> CMKVersion:
    return version_from_env()


@pytest.fixture(name="client")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="checkmk")
def _checkmk(client: docker.DockerClient) -> docker.models.containers.Container:
    with start_checkmk(client, name="checkmk", ports={"8000/tcp": 9000}) as container:
        yield container


@pytest.fixture(name="oracle")
def _oracle(
    client: docker.DockerClient,
    checkmk: docker.models.containers.Container,
    tmp_path: Path,
) -> docker.models.containers.Container:
    with _start_oracle(
        client,
        checkmk,
        root_dir=tmp_path,
        name="oracle",
    ) as container:
        yield container


@dataclass
class OracleDatabase:
    SID: str = "FREE"
    PDB: str = "FREEPDB1"
    PWD: str = "oracle"
    CHARSET: str = "AL32UTF8"
    # user name; use "c##<name>" notation for pluggable databases
    USER: str = "c##checkmk"
    PORT: int = 1521
    UID: int = 54321
    ORADATA: str = "oradata"
    ORAENV: str = "oraenv"

    SYS_AUTH: str = f"sys/{PWD}@localhost:{PORT}/{SID}"

    environment = {
        "ORACLE_SID": SID,
        "ORACLE_PDB": PDB,
        "ORACLE_PWD": PWD,
        "ORACLE_CHARACTERSET": CHARSET,
        "MK_CONFDIR": "/etc/check_mk",
        "MK_VARDIR": "/var/lib/check_mk_agent",
    }

    mk_service_cfg = "\n".join(
        [
            "MAX_TASKS=10",
            f"DBUSER='{USER}:cmk::localhost:1521:FREE'",
        ]
    )
    create_user_sql = "\n".join(
        [
            f"CREATE USER IF NOT EXISTS {USER} IDENTIFIED BY cmk;",
            f"ALTER USER {USER} SET container_data=all container=current;",
            f"GRANT select_catalog_role TO {USER} container=all;",
            f"GRANT create session TO {USER} container=all;",
        ]
    )
    register_listener_sql = "ALTER SYSTEM REGISTER;"
    restart_oracle_sql = "SHUTDOWN IMMEDIATE;\nSTARTUP;"


def _pull_oracle(docker_client: docker.DockerClient) -> docker.models.containers.Image:
    logger.info("Downloading Oracle Database Free docker image")
    return docker_client.images.pull(resolve_image_alias("IMAGE_ORACLE_DB_23C"))


def _install_oracle_plugin(container: docker.models.containers.Container) -> None:
    plugin_source_path = str(repo_path() / "agents" / "plugins" / "mk_oracle")
    plugin_target_folder = "/usr/lib/check_mk_agent/plugins"

    logger.info("Patching the Oracle plugin: Detect free edition + Use default TNS_ADMIN path...")
    with open(plugin_source_path, "r") as plugin_file:
        plugin_script = plugin_file.read()
    # detect free edition
    plugin_script = plugin_script.replace(r"_pmon_'", r"_pmon_|^db_pmon_'")
    # use default TNS_ADMIN path
    plugin_script = plugin_script.replace(
        r"TNS_ADMIN=${TNS_ADMIN:-$MK_CONFDIR}",
        r"TNS_ADMIN=${TNS_ADMIN:-${ORACLE_HOME}/network/admin}",
    )
    plugin_source_path = "/tmp/mk_oracle"
    with open(plugin_source_path, "w") as plugin_file:
        plugin_file.write(plugin_script)

    logger.info('Installing Oracle plugin "%s"...', plugin_source_path)
    assert copy_to_container(container, plugin_source_path, plugin_target_folder)

    container.exec_run(
        rf'chmod +x "{plugin_target_folder}/mk_oracle"', user="root", privileged=True
    )
    container.exec_run(
        r"""bash -c 'ln -s "${ORACLE_HOME}/perl/bin/perl" "/usr/bin/perl"'""",
        user="root",
        privileged=True,
    )


@contextmanager
def _start_oracle(
    client: docker.DockerClient,
    checkmk: docker.models.containers.Container,
    root_dir: Path,
    name: str = "oracle",
) -> Iterator[docker.models.containers.Container]:
    oracle_image = _pull_oracle(client)
    db = OracleDatabase()

    site_ip = get_container_ip(checkmk)
    assert site_ip

    site_id = "cmk"
    api_user = "automation"
    api_secret = checkmk_docker_automation_secret(checkmk, site_id, api_user)

    oraenv = Path(root_dir / db.ORAENV).as_posix()
    oradata = Path(root_dir / db.ORADATA).as_posix()

    makedirs(oraenv)
    execute(["chmod", "775", oradata])
    execute(["chown", f"{db.UID}", oraenv])
    write_file(f"{oraenv}/mk_oracle.cfg", db.mk_service_cfg)
    write_file(f"{oraenv}/create_user.sql", db.create_user_sql)
    write_file(f"{oraenv}/register_listener.sql", db.register_listener_sql)
    write_file(f"{oraenv}/restart_oracle.sql", db.restart_oracle_sql)

    volumes = [f"{oraenv}:/opt/oracle/oraenv"]
    makedirs(oradata)
    execute(["chmod", "775", oradata])
    execute(["chown", str(db.UID), oradata])
    volumes.append(f"{oradata}:/opt/oracle/oradata")

    try:
        oracle: docker.models.containers.Container = client.containers.get(name)
        if os.getenv("REUSE") == "1":
            oracle.start()
        else:
            oracle.remove(force=True)
    except docker.errors.NotFound:
        oracle = client.containers.run(
            image=oracle_image.id,
            name=name,
            volumes=volumes,
            environment=db.environment,
            detach=True,
            shm_size="1G",
            mem_limit="6G",
        )

    logger.info("Starting container %s from image %s", oracle.short_id, oracle_image.short_id)

    done_msg = "DATABASE IS READY TO USE!"
    try:
        wait_until(lambda: done_msg in oracle.logs().decode("utf-8"), timeout=600)
        output = oracle.logs().decode("utf-8")

        assert done_msg in output
    except:
        logger.error(oracle.logs().decode("utf-8"))
        raise

    logger.info("Force listener registration")
    rc, _ = oracle.exec_run(
        """bash -c 'sqlplus -s "/ as sysdba" < "/opt/oracle/oraenv/register_listener.sql"'""",
    )
    assert rc == 0, "Error during listener registration"

    logger.info('Creating Checkmk user "%s"', db.USER)
    rc, _ = oracle.exec_run(
        """bash -c 'sqlplus -s "/ as sysdba" < "/opt/oracle/oraenv/create_user.sql"'""",
    )
    assert rc == 0, "Error during user creation"

    # reload() to make sure all attributes are set (e.g. NetworkSettings)
    oracle.reload()

    checkmk_install_agent(app=oracle, checkmk=checkmk)

    checkmk_install_agent_controller_daemon(app=oracle)

    _install_oracle_plugin(container=oracle)

    checkmk_docker_add_host(
        checkmk=checkmk,
        hostname=name,
        ipv4=get_container_ip(oracle),
    )

    checkmk_register_agent(
        oracle,
        site_ip=get_container_ip(checkmk),
        site_id=site_id,
        hostname=name,
        api_user=api_user,
        api_secret=api_secret,
    )

    checkmk_docker_wait_for_services(checkmk=checkmk, hostname=name, min_services=5)

    logger.debug(oracle.logs().decode("utf-8"))

    try:
        yield oracle
    finally:
        oracle.stop()
        if os.getenv("CLEANUP", "1") == "1":
            oracle.remove(force=True)
