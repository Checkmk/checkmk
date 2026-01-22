#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import pytest

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig, Secret, SystemBinary, SystemConfig
from cmk.plugins.oracle.bakery.mk_oracle_unified import (
    bakery_plugin_oracle,
    GuiAdditionalOptionsConf,
    GuiAuthUserPasswordData,
    GuiConfig,
    GuiConnectionConf,
    GuiDiscoveryConf,
    GuiInstanceAuthUserPasswordData,
    GuiInstanceConf,
    GuiMainConf,
    GuiOracleClientLibOptions,
    GuiOracleIdentificationConf,
)

PLUGIN_NAME = "mk_oracle_unified"

STANDARD_AUTH: Literal["standard"] = "standard"
DEPLOY: Literal["deploy"] = "deploy"
CMK_POSTPROCESSED: Literal["cmk_postprocessed"] = "cmk_postprocessed"
EXPLICIT_PASSWORD: Literal["explicit_password"] = "explicit_password"
ALWAYS_ORACLE_LIB_OPTION: Literal["always"] = "always"
CUSTOM_ORACLE_LIB_OPTION: Literal["custom"] = "custom"


def _source(base_os: OS) -> Path:
    return Path("mk-oracle" if base_os == OS.LINUX else "mk-oracle.exe")


def _target(base_os: OS) -> Path:
    return (
        Path("packages", "mk-oracle", "mk-oracle")
        if base_os == OS.LINUX
        else Path("packages", "mk-oracle", "mk-oracle.exe")
    )


linux_files: list[Plugin] = [
    Plugin(
        base_os=OS.LINUX,
        source=Path("mk-oracle"),
        target=Path("packages", "mk-oracle", "mk-oracle"),
    ),
    Plugin(
        base_os=OS.LINUX,
        source=Path("oracle_unified_sync"),
        target=Path("oracle_unified_sync"),
    ),
    Plugin(
        base_os=OS.LINUX,
        source=Path("oracle_unified_async"),
        target=Path("oracle_unified_async"),
        interval=600,
    ),
]

windows_files: list[Plugin] = [
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("mk-oracle.exe"),
        target=Path("packages", "mk-oracle", "mk-oracle.exe"),
    ),
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("oracle_unified_sync.ps1"),
        target=Path("oracle_unified_sync.ps1"),
    ),
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("oracle_unified_async.ps1"),
        target=Path("oracle_unified_async.ps1"),
        interval=600,
    ),
]

files_base: list[Plugin] = linux_files + windows_files


def _combine(files: Sequence[Plugin], yaml_lines: Sequence[str]) -> Sequence[Plugin | PluginConfig]:
    ret = list(files) + [
        PluginConfig(base_os=base_os, lines=list(yaml_lines), target=Path("oracle.yml"))
        for base_os in (OS.LINUX, OS.WINDOWS)
    ]

    return sorted(ret, key=lambda x: str(x.base_os))


# 1. Minimal config (already present)
oracle_config_min: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="cmk",
                password=Secret("pw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=None,
            timeout=None,
            tns_admin=None,
            oracle_id=None,
        ),
        options=None,
        cache_age=None,
        discovery=None,
        sections=None,
    ),
    instances=None,
)

expected_yaml_lines_min = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: pw",
    "      type: standard",
    "      username: cmk",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
]

# 2. Full config
oracle_config_full: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="admin",
                password=Secret("adminpw", "", ""),
                role="sysdba",
            ),
        ),
        connection=GuiConnectionConf(
            host="dbhost",
            port=1521,
            timeout=10,
            tns_admin="/etc/oracle/tns",
            oracle_id=None,
        ),
        options=GuiAdditionalOptionsConf(
            max_connections=10,
            max_queries=100,
            ignore_db_name=True,
            oracle_client_library=None,
        ),
        cache_age=600,
        discovery=GuiDiscoveryConf(
            enabled=True,
            include=["prod*", "test*"],
            exclude=["old*"],
        ),
        sections={
            "instance": "synchronous",
            "asm_instance": "disabled",
            "dataguard_stats": "disabled",
            "locks": "disabled",
            "logswitches": "disabled",
            "longactivesessions": "disabled",
            "performance": "asynchronous",
            "processes": "disabled",
            "recovery_area": "disabled",
            "recovery_status": "disabled",
            "sessions": "disabled",
            "systemparameter": "disabled",
            "undostat": "disabled",
            "asm_diskgroup": "disabled",
            "iostats": "disabled",
            "jobs": "disabled",
            "resumable": "disabled",
            "rman": "disabled",
            "tablespaces": "disabled",
        },
    ),
    instances=[
        GuiInstanceConf(
            service_name="Service_Name_1",
            instance_name=None,
            auth=None,
            connection=None,
        ),
        GuiInstanceConf(
            service_name="Service_Name_2",
            instance_name="Instance_Name_2",
            auth=(
                STANDARD_AUTH,
                GuiInstanceAuthUserPasswordData(
                    username="inst2",
                    password=Secret("inst2pw", "", ""),
                    role=None,
                ),
            ),
            connection=GuiConnectionConf(
                host="dbhost2",
                port=1522,
                timeout=20,
                tns_admin="/etc/oracle/tns2",
                oracle_id=None,
            ),
        ),
        GuiInstanceConf(
            service_name=None,
            instance_name=None,
            auth=None,
            connection=None,
        ),
    ],
)

expected_yaml_lines_full = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: adminpw",
    "      role: sysdba",
    "      type: standard",
    "      username: admin",
    "    cache_age: 600",
    "    connection:",
    "      hostname: dbhost",
    "      port: 1521",
    "      timeout: 10",
    "      tns_admin: /etc/oracle/tns",
    "    discovery:",
    "      enabled: true",
    "      exclude:",
    "      - old*",
    "      include:",
    "      - prod*",
    "      - test*",
    "    instances:",
    "    - service_name: Service_Name_1",
    "    - authentication:",
    "        password: inst2pw",
    "        type: standard",
    "        username: inst2",
    "      connection:",
    "        hostname: dbhost2",
    "        port: 1522",
    "        timeout: 20",
    "        tns_admin: /etc/oracle/tns2",
    "      instance_name: Instance_Name_2",
    "      service_name: Service_Name_2",
    "    options:",
    "      ignore_db_name: 1",
    "      max_connections: 10",
    "      max_queries: 100",
    "    sections:",
    "    - instance:",
    "        is_async: false",
    "    - performance:",
    "        is_async: true",
]

# 3. Main config with auth, connection and one section
oracle_config_section: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="secuser",
                password=Secret("secpw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=1521,
            timeout=None,
            tns_admin="some_tns_admin",
            oracle_local_registry="some_registry",
            oracle_id=GuiOracleIdentificationConf(
                service_name="some_name", instance_name="some_instance"
            ),
        ),
        options=None,
        cache_age=None,
        discovery=None,
        sections={
            "instance": "synchronous",
            "asm_instance": "disabled",
            "dataguard_stats": "disabled",
            "locks": "disabled",
            "logswitches": "disabled",
            "longactivesessions": "disabled",
            "performance": "disabled",
            "processes": "disabled",
            "recovery_area": "disabled",
            "recovery_status": "disabled",
            "sessions": "disabled",
            "systemparameter": "disabled",
            "undostat": "disabled",
            "asm_diskgroup": "disabled",
            "iostats": "disabled",
            "jobs": "disabled",
            "resumable": "disabled",
            "rman": "disabled",
            "tablespaces": "disabled",
        },
    ),
    instances=None,
)

expected_yaml_lines_section = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: secpw",
    "      type: standard",
    "      username: secuser",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "      instance: some_instance",
    "      oracle_local_registry: some_registry",
    "      port: 1521",
    "      service_name: some_name",
    "      tns_admin: some_tns_admin",
    "    sections:",
    "    - instance:",
    "        is_async: false",
]

# 4. Main config with auth, connection and instances with only one instance (only sid)
oracle_config_instance_sid: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="onlysid",
                password=Secret("sidpw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=None,
            timeout=None,
            tns_admin=None,
        ),
        options=None,
        cache_age=None,
        discovery=None,
        sections=None,
    ),
    instances=[
        GuiInstanceConf(
            service_name="SIDONLY",
            instance_name=None,
            auth=None,
            connection=None,
        ),
    ],
)

expected_yaml_lines_instance_sid = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: sidpw",
    "      type: standard",
    "      username: onlysid",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "    instances:",
    "    - service_name: SIDONLY",
]

# 5. Main config with auth, connection, discovery and two instances (one only sid, one full)
oracle_config_discovery_instances: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="mainuser",
                password=Secret("mainpw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=1521,
            timeout=5,
            tns_admin=None,
        ),
        options=None,
        cache_age=None,
        discovery=GuiDiscoveryConf(
            enabled=True,
            include=None,
            exclude=None,
        ),
        sections=None,
    ),
    instances=[
        GuiInstanceConf(
            service_name=None,
            instance_name="SID_A",
            auth=None,
            connection=None,
        ),
        GuiInstanceConf(
            service_name=None,
            instance_name="SID_B",
            auth=(
                STANDARD_AUTH,
                GuiInstanceAuthUserPasswordData(
                    username="buser",
                    password=Secret("bpw", "", ""),
                    role="sysdba",
                ),
            ),
            connection=GuiConnectionConf(
                host="hostb",
                port=1522,
                timeout=10,
                tns_admin="/etc/oracle/tnsb",
            ),
        ),
    ],
)

expected_yaml_lines_discovery_instances = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: mainpw",
    "      type: standard",
    "      username: mainuser",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "      port: 1521",
    "      timeout: 5",
    "    discovery:",
    "      enabled: true",
    "    instances:",
    "    - instance_name: SID_A",
    "    - authentication:",
    "        password: bpw",
    "        role: sysdba",
    "        type: standard",
    "        username: buser",
    "      connection:",
    "        hostname: hostb",
    "        port: 1522",
    "        timeout: 10",
    "        tns_admin: /etc/oracle/tnsb",
    "      instance_name: SID_B",
]

# 6. Main config with auth, connection and additional option use_host_client set to 'always'
oracle_config_use_host_client_always: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="user",
                password=Secret("pw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=1521,
            timeout=None,
            tns_admin=None,
            oracle_local_registry=None,
        ),
        options=GuiAdditionalOptionsConf(
            oracle_client_library=GuiOracleClientLibOptions(
                use_host_client=(ALWAYS_ORACLE_LIB_OPTION, None),
            )
        ),
        cache_age=None,
        discovery=None,
        sections=None,
    ),
    instances=None,
)

expected_yaml_lines_use_host_client_always = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: pw",
    "      type: standard",
    "      username: user",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "      port: 1521",
    "    options:",
    "      use_host_client: always",
]

# 7. Main config with auth, connection and additional option use_host_client set to path
oracle_config_use_host_client_path: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="user",
                password=Secret("pw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=1521,
            timeout=None,
            tns_admin=None,
            oracle_local_registry=None,
        ),
        options=GuiAdditionalOptionsConf(
            oracle_client_library=GuiOracleClientLibOptions(
                use_host_client=(CUSTOM_ORACLE_LIB_OPTION, "/path/to/client"),
            )
        ),
        cache_age=None,
        discovery=None,
        sections=None,
    ),
    instances=None,
)

expected_yaml_lines_use_host_client_path = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: pw",
    "      type: standard",
    "      username: user",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "      port: 1521",
    "    options:",
    "      use_host_client: /path/to/client",
]

# 8. Main config with auth, connection and additional option deploy_lib
# set to True to deploy oracle binaries
oracle_config_deploy_oracle_binaries: GuiConfig = GuiConfig(
    deploy=(DEPLOY, None),
    main=GuiMainConf(
        auth=(
            STANDARD_AUTH,
            GuiAuthUserPasswordData(
                username="user",
                password=Secret("pw", "", ""),
                role=None,
            ),
        ),
        connection=GuiConnectionConf(
            host="localhost",
            port=1521,
            timeout=None,
            tns_admin=None,
            oracle_local_registry=None,
        ),
        options=GuiAdditionalOptionsConf(
            oracle_client_library=GuiOracleClientLibOptions(
                deploy_lib=True,
            )
        ),
        cache_age=None,
        discovery=None,
        sections=None,
    ),
    instances=None,
)

expected_yaml_lines_deploy_oracle_binaries = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: pw",
    "      type: standard",
    "      username: user",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "      port: 1521",
]


def _process(config: GuiConfig) -> Sequence[Plugin | PluginConfig | SystemBinary | SystemConfig]:
    return list(
        bakery_plugin_oracle.files_function(
            bakery_plugin_oracle.parameter_parser(config.model_dump())
        )
    )


@pytest.mark.parametrize(
    ["config", "expected"],
    [
        (oracle_config_min, expected_yaml_lines_min),
        (oracle_config_full, expected_yaml_lines_full),
        (oracle_config_section, expected_yaml_lines_section),
        (oracle_config_instance_sid, expected_yaml_lines_instance_sid),
        (oracle_config_discovery_instances, expected_yaml_lines_discovery_instances),
        (oracle_config_use_host_client_always, expected_yaml_lines_use_host_client_always),
        (oracle_config_use_host_client_path, expected_yaml_lines_use_host_client_path),
    ],
)
def test_oracle_min(config: GuiConfig, expected: Sequence[str]) -> None:
    assert _process(config) == _combine(files_base, expected), "name"
