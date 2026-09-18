#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import pytest

from cmk.bakery.v2 import OS, Plugin, PluginConfig, Secret, SystemBinary, SystemConfig
from cmk.plugins.oracle.bakery.mk_oracle_unified import (
    BakedAuthConf,
    BakedAuthUserPasswordData,
    BakedConfig,
    BakedInstanceConf,
    bakery_plugin_oracle,
)
from cmk.plugins.oracle.lib.unified_config import (
    StoredConnectionConf,
    StoredDescriptorConf,
    StoredDiscoveryConf,
    StoredExcludedSectionConf,
    StoredOracleSafeEntries,
)

PLUGIN_NAME = "mk_oracle_unified"

DEPLOY: Literal["deploy"] = "deploy"
CMK_POSTPROCESSED: Literal["cmk_postprocessed"] = "cmk_postprocessed"
EXPLICIT_PASSWORD: Literal["explicit_password"] = "explicit_password"
ALWAYS_ORACLE_LIB_OPTION: Literal["always"] = "always"
CUSTOM_ORACLE_LIB_OPTION: Literal["custom"] = "custom"


def _source(base_os: OS) -> Path:
    match base_os:
        case OS.LINUX:
            return Path("mk-oracle")
        case OS.WINDOWS:
            return Path("mk-oracle.exe")
        case OS.AIX:
            return Path("mk-oracle.aix")
        case OS.SOLARIS:
            return Path("mk-oracle.solaris")
        case _:
            raise ValueError(f"Unsupported OS: {base_os}")


def _target(base_os: OS) -> Path:
    match base_os:
        case OS.LINUX:
            return Path("libexec", "mk-oracle-v2", "mk-oracle-v2")
        case OS.WINDOWS:
            return Path("libexec", "mk-oracle-v2", "mk-oracle-v2.exe")
        case OS.AIX:
            return Path("libexec", "mk-oracle-v2", "mk-oracle-v2.aix")
        case OS.SOLARIS:
            return Path("libexec", "mk-oracle-v2", "mk-oracle-v2.solaris")
        case _:
            raise ValueError(f"Unsupported OS: {base_os}")


linux_files: list[Plugin] = [
    Plugin(
        base_os=OS.LINUX,
        source=Path("mk-oracle"),
        target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2"),
    ),
    Plugin(
        base_os=OS.LINUX,
        source=Path("oracle_unified_sync"),
        target=Path("mk-oracle-v2_sync"),
    ),
    Plugin(
        base_os=OS.LINUX,
        source=Path("oracle_unified_async"),
        target=Path("mk-oracle-v2_async"),
        interval=600,
    ),
]

windows_files: list[Plugin] = [
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("mk-oracle.exe"),
        target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2.exe"),
    ),
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("oracle_unified_sync.ps1"),
        target=Path("mk-oracle-v2_sync.ps1"),
    ),
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("oracle_unified_async.ps1"),
        target=Path("mk-oracle-v2_async.ps1"),
        interval=600,
    ),
]

aix_files: list[Plugin] = [
    Plugin(
        base_os=OS.AIX,
        source=Path("mk-oracle.aix"),
        target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2.aix"),
    ),
    Plugin(
        base_os=OS.AIX,
        source=Path("oracle_unified_sync.aix"),
        target=Path("mk-oracle-v2_sync.aix"),
    ),
    Plugin(
        base_os=OS.AIX,
        source=Path("oracle_unified_async.aix"),
        target=Path("mk-oracle-v2_async.aix"),
        interval=600,
    ),
]

solaris_files: list[Plugin] = [
    Plugin(
        base_os=OS.SOLARIS,
        source=Path("mk-oracle.solaris"),
        target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2.solaris"),
    ),
    Plugin(
        base_os=OS.SOLARIS,
        source=Path("oracle_unified_sync.solaris"),
        target=Path("mk-oracle-v2_sync.solaris"),
    ),
    Plugin(
        base_os=OS.SOLARIS,
        source=Path("oracle_unified_async.solaris"),
        target=Path("mk-oracle-v2_async.solaris"),
        interval=600,
    ),
]

files_base: list[Plugin] = linux_files + windows_files + aix_files + solaris_files


def _combine(files: Sequence[Plugin], yaml_lines: Sequence[str]) -> Sequence[Plugin | PluginConfig]:
    ret = list(files) + [
        PluginConfig(base_os=base_os, lines=list(yaml_lines), target=Path("mk-oracle.yml"))
        for base_os in (OS.LINUX, OS.WINDOWS, OS.AIX, OS.SOLARIS)
    ]

    return sorted(ret, key=lambda x: str(x.base_os))


# 1. Minimal config (already present)
oracle_config_min: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="cmk",
                password=Secret("pw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=None,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=None,
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
    "    custom_metrics_cache_age: 600",
]

# 2. Full config
oracle_config_full: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    max_connections=10,
    ignore_db_name=True,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="admin",
                password=Secret("adminpw", "", ""),
            ),
        ),
        role="sysdba",
    ),
    connection=StoredConnectionConf(
        host="dbhost",
        port=1521,
        timeout=10,
    ),
    tns_admin="/etc/oracle/tns",
    cache_age=600,
    discovery=StoredDiscoveryConf(
        enabled="enabled",
        include=["prod*", "test*"],
        exclude=["old*"],
    ),
    sections={
        "performance": True,
    },
    instances_rev2=[
        BakedInstanceConf(
            oracle_id=(
                "descriptor",
                StoredDescriptorConf(
                    service_name="Service_Name_1",
                ),
            ),
        ),
        BakedInstanceConf(
            oracle_id=(
                "descriptor",
                StoredDescriptorConf(
                    service_name="Service_Name_2",
                    instance_name="Instance_Name_2",
                ),
            ),
            auth=BakedAuthConf(
                auth_type=(
                    "standard",
                    BakedAuthUserPasswordData(
                        username="inst2",
                        password=Secret("inst2pw", "", ""),
                    ),
                ),
                role=None,
            ),
            connection=StoredConnectionConf(
                host="dbhost2",
                port=1522,
                timeout=20,
            ),
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
    "    custom_metrics_cache_age: 600",
    "    discovery:",
    "      detect: true",
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
    "      instance_name: Instance_Name_2",
    "      service_name: Service_Name_2",
    "    options:",
    "      ignore_db_name: 1",
    "      max_connections: 10",
    "    sections:",
    "    - instance:",
    "        is_async: false",
    "    - asm_instance:",
    "        is_async: false",
    "    - performance:",
    "        is_async: true",
]

# 3. Main config with auth, connection and one section
oracle_config_section: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="secuser",
                password=Secret("secpw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=1521,
        timeout=None,
    ),
    tns_admin="some_tns_admin",
    oracle_local_registry="some_registry",
    cache_age=None,
    discovery=None,
    sections={},
    instances_rev2=None,
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
    "      oracle_local_registry: some_registry",
    "      port: 1521",
    "      tns_admin: some_tns_admin",
    "    custom_metrics_cache_age: 600",
    "    sections:",
    "    - instance:",
    "        is_async: false",
    "    - asm_instance:",
    "        is_async: false",
]

# 4. Main config with auth, connection and instances with only one instance (only sid)
oracle_config_instance_sid: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="onlysid",
                password=Secret("sidpw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=None,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=[
        BakedInstanceConf(
            oracle_id=(
                "descriptor",
                StoredDescriptorConf(
                    service_name="SIDONLY",
                ),
            ),
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
    "    custom_metrics_cache_age: 600",
    "    instances:",
    "    - service_name: SIDONLY",
]

# 5. Main config with auth, connection, discovery and two instances (one only sid, one full)
oracle_config_discovery_instances: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="mainuser",
                password=Secret("mainpw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=1521,
        timeout=5,
    ),
    cache_age=None,
    discovery=StoredDiscoveryConf(
        enabled="enabled",
        include=None,
        exclude=None,
    ),
    sections=None,
    instances_rev2=[
        BakedInstanceConf(
            oracle_id=(
                "descriptor",
                StoredDescriptorConf(
                    instance_name="SID_A",
                ),
            ),
        ),
        BakedInstanceConf(
            oracle_id=(
                "descriptor",
                StoredDescriptorConf(
                    instance_name="SID_B",
                ),
            ),
            auth=BakedAuthConf(
                auth_type=(
                    "standard",
                    BakedAuthUserPasswordData(
                        username="buser",
                        password=Secret("bpw", "", ""),
                    ),
                ),
                role="sysdba",
            ),
            connection=StoredConnectionConf(
                host="hostb",
                port=1522,
                timeout=10,
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
    "    custom_metrics_cache_age: 600",
    "    discovery:",
    "      detect: true",
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
    "      instance_name: SID_B",
]

# 6. Main config with auth, connection and additional option use_host_client set to 'always'
oracle_config_use_host_client_always: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    use_host_client=(ALWAYS_ORACLE_LIB_OPTION, None),
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="user",
                password=Secret("pw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=1521,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=None,
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
    "    custom_metrics_cache_age: 600",
    "    options:",
    "      use_host_client: always",
]

# 7. Main config with auth, connection and additional option use_host_client set to path
oracle_config_use_host_client_path: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    use_host_client=(CUSTOM_ORACLE_LIB_OPTION, "/path/to/client"),
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="user",
                password=Secret("pw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=1521,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=None,
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
    "    custom_metrics_cache_age: 600",
    "    options:",
    "      use_host_client: /path/to/client",
]

# 8. Main config with auth, connection and additional option deploy_lib
# 8. Main config with auth and connection only
oracle_config_deploy_oracle_binaries: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="user",
                password=Secret("pw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=1521,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=None,
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
    "    custom_metrics_cache_age: 600",
]

# 9. Main config with wallet auth, connection
oracle_config_wallet_auth: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "wallet",
            None,
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=1521,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=None,
)

expected_yaml_lines_wallet_auth = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      type: wallet",
    "    cache_age: 600",
    "    connection:",
    "      hostname: localhost",
    "      port: 1521",
    "    custom_metrics_cache_age: 600",
]


def _process(config: BakedConfig) -> Sequence[Plugin | PluginConfig | SystemBinary | SystemConfig]:
    return sorted(
        bakery_plugin_oracle.files_function(
            bakery_plugin_oracle.parameter_parser(config.model_dump())
        ),
        key=lambda x: str(x.base_os),
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
        (oracle_config_deploy_oracle_binaries, expected_yaml_lines_deploy_oracle_binaries),
        (oracle_config_wallet_auth, expected_yaml_lines_wallet_auth),
    ],
)
def test_oracle_min(config: BakedConfig, expected: Sequence[str]) -> None:
    assert _process(config) == _combine(files_base, expected), "name"


# --- custom_metrics_cache_age tests ---

oracle_config_custom_metrics_cache_age: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="cmk",
                password=Secret("pw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host="localhost",
        port=None,
        timeout=None,
    ),
    cache_age=None,
    custom_metrics_cache_age=120,
    discovery=None,
    sections=None,
    instances_rev2=None,
)

expected_yaml_lines_custom_metrics_cache_age = [
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
    "    custom_metrics_cache_age: 120",
]


custom_metrics_files: list[Plugin] = [
    Plugin(
        base_os=OS.LINUX,
        source=Path("oracle_unified_async_custom_metrics"),
        target=Path("mk-oracle-v2_async_custom_metrics"),
        interval=120,
    ),
    Plugin(
        base_os=OS.WINDOWS,
        source=Path("oracle_unified_async_custom_metrics.ps1"),
        target=Path("mk-oracle-v2_async_custom_metrics.ps1"),
        interval=120,
    ),
    Plugin(
        base_os=OS.AIX,
        source=Path("oracle_unified_async_custom_metrics.aix"),
        target=Path("mk-oracle-v2_async_custom_metrics.aix"),
        interval=120,
    ),
    Plugin(
        base_os=OS.SOLARIS,
        source=Path("oracle_unified_async_custom_metrics.solaris"),
        target=Path("mk-oracle-v2_async_custom_metrics.solaris"),
        interval=120,
    ),
]


# The rule may leave the host unset. The plug-in then picks its own default,
# which is the node name on a host running Grid Infrastructure and localhost
# elsewhere, so the bakery must not decide it here.
oracle_config_no_host: BakedConfig = BakedConfig(
    deploy_rev2=DEPLOY,
    auth=BakedAuthConf(
        auth_type=(
            "standard",
            BakedAuthUserPasswordData(
                username="cmk",
                password=Secret("pw", "", ""),
            ),
        ),
        role=None,
    ),
    connection=StoredConnectionConf(
        host=None,
        port=None,
        timeout=None,
    ),
    cache_age=None,
    discovery=None,
    sections=None,
    instances_rev2=None,
)

expected_yaml_lines_no_host = [
    "---",
    "oracle:",
    "  main:",
    "    authentication:",
    "      password: pw",
    "      type: standard",
    "      username: cmk",
    "    cache_age: 600",
    "    custom_metrics_cache_age: 600",
]


def test_oracle_without_host_omits_hostname() -> None:
    assert _process(oracle_config_no_host) == _combine(files_base, expected_yaml_lines_no_host)


def test_oracle_without_host_keeps_other_connection_keys() -> None:
    config = oracle_config_no_host.model_copy(deep=True)
    config.connection = StoredConnectionConf(host=None, port=1234, timeout=None)
    lines = [
        line
        for entry in _process(config)
        if isinstance(entry, PluginConfig)
        for line in entry.lines
    ]
    assert "      port: 1234" in lines
    assert not any(line.strip().startswith("hostname:") for line in lines)


def test_custom_metrics_cache_age_in_yaml() -> None:
    assert _process(oracle_config_custom_metrics_cache_age) == _combine(
        files_base + custom_metrics_files, expected_yaml_lines_custom_metrics_cache_age
    )


def test_no_custom_metrics_files_when_cache_ages_equal() -> None:
    config = BakedConfig(
        deploy_rev2=DEPLOY,
        auth=BakedAuthConf(
            auth_type=(
                "standard",
                BakedAuthUserPasswordData(username="cmk", password=Secret("pw", "", "")),
            ),
            role=None,
        ),
        connection=StoredConnectionConf(host="localhost", port=None, timeout=None),
        cache_age=300,
        custom_metrics_cache_age=300,
        instances_rev2=None,
    )
    result = _process(config)
    custom_metrics_sources = [
        p for p in result if isinstance(p, Plugin) and "custom_metrics" in str(p.source)
    ]
    assert custom_metrics_sources == []


@pytest.mark.parametrize(
    ["custom_metrics_cache_age", "expected"],
    [
        (None, 600),
        (120, 120),
        (30, 30),
        (900, 900),
    ],
)
def test_get_active_custom_metrics_cache_age(
    custom_metrics_cache_age: int | None, expected: int
) -> None:
    conf = BakedConfig(
        deploy_rev2=DEPLOY,
        auth=BakedAuthConf(
            auth_type=(
                "standard",
                BakedAuthUserPasswordData(username="u", password=Secret("p", "", "")),
            ),
            role=None,
        ),
        connection=StoredConnectionConf(host="localhost", port=None, timeout=None),
        custom_metrics_cache_age=custom_metrics_cache_age,
    )
    assert conf.get_active_custom_metrics_cache_age() == expected


def _parsed(**stored: object) -> BakedConfig:
    return BakedConfig.model_validate(
        {"deploy_rev2": DEPLOY, "auth": {}, "connection": {}, **stored}
    )


def test_additional_options_parses_validate_permissions_enabled() -> None:
    parsed = _parsed(validate_permissions=("enabled", {"safe_entries": ["grp1", "user2"]}))
    assert parsed.validate_permissions == (
        "enabled",
        StoredOracleSafeEntries(safe_entries=["grp1", "user2"]),
    )


def test_additional_options_parses_validate_permissions_disabled() -> None:
    assert _parsed(validate_permissions=("disabled", None)).validate_permissions == (
        "disabled",
        None,
    )


def test_additional_options_ignores_legacy_permissions_check_key() -> None:
    # Regression guard: the ruleset key is `validate_permissions`. A stray `permissions_check`
    # key (the previous, wrong field name) must not bind and is ignored.
    assert (
        _parsed(permissions_check=("enabled", {"safe_entries": ["x"]})).validate_permissions is None
    )


# --- excluded_sections tests ---

SID: Literal["sid"] = "sid"
DESCRIPTOR: Literal["descriptor"] = "descriptor"
ALIAS: Literal["alias"] = "alias"


def _config_with_excluded_sections(
    excluded_sections: list[StoredExcludedSectionConf] | None,
) -> BakedConfig:
    return BakedConfig(
        deploy_rev2=DEPLOY,
        auth=BakedAuthConf(
            auth_type=(
                "standard",
                BakedAuthUserPasswordData(username="cmk", password=Secret("pw", "", "")),
            ),
            role=None,
        ),
        connection=StoredConnectionConf(host="localhost", port=None, timeout=None),
        excluded_sections=excluded_sections,
        instances_rev2=None,
    )


def test_the_bakery_says_so_when_no_rule_asked_for_a_deployment() -> None:
    config = BakedConfig.model_validate({"auth": {"auth_type": ("wallet", None)}})
    with pytest.raises(ValueError, match="whether to deploy"):
        _process(config)


def test_the_bakery_says_so_when_no_rule_named_credentials() -> None:
    config = BakedConfig.model_validate({"deploy_rev2": DEPLOY})
    with pytest.raises(ValueError, match="no credentials"):
        _process(config)


def test_the_oracle_file_paths_survive_without_a_connection() -> None:
    config = BakedConfig.model_validate(
        {
            "deploy_rev2": DEPLOY,
            "auth": {"auth_type": ("wallet", None)},
            "tns_admin": "/etc/oracle",
        }
    )
    assert "      tns_admin: /etc/oracle" in _yaml_lines(config)


def _yaml_lines(config: BakedConfig) -> Sequence[str]:
    entries = [entry for entry in _process(config) if isinstance(entry, PluginConfig)]
    assert entries, "no plugin config emitted"
    return list(entries[0].lines)


def test_excluded_sections_emits_the_target_fields_and_the_sections() -> None:
    # The ruleset value is a tagged tuple; the tag is dropped and the identifying
    # fields are written next to `sections`, without a `target_id` level.
    config = _config_with_excluded_sections(
        [
            StoredExcludedSectionConf(
                target_id=(SID, "XE"),
                sections=["jobs", "tablespaces"],
            )
        ]
    )

    lines = _yaml_lines(config)

    assert "    excluded_sections:" in lines
    assert "    - sections:" in lines
    assert "      - jobs" in lines
    assert "      - tablespaces" in lines
    assert "      sid: XE" in lines
    # The cascading tag itself is never emitted.
    assert not any("descriptor" in line for line in lines)


def test_excluded_sections_emits_every_identifying_field_of_a_descriptor() -> None:
    config = _config_with_excluded_sections(
        [
            StoredExcludedSectionConf(
                target_id=(
                    DESCRIPTOR,
                    StoredDescriptorConf(service_name="srv", instance_name="inst", sid="XE"),
                ),
                sections=["jobs"],
            )
        ]
    )

    lines = _yaml_lines(config)

    # The dumper sorts the keys, so `instance_name` opens the entry.
    assert "    - instance_name: inst" in lines
    assert "      service_name: srv" in lines
    assert "      sid: XE" in lines


def test_excluded_sections_emits_an_alias_target() -> None:
    config = _config_with_excluded_sections(
        [
            StoredExcludedSectionConf(
                target_id=(ALIAS, "my_alias"),
                sections=["locks"],
            )
        ]
    )

    assert "    - alias: my_alias" in _yaml_lines(config)


def test_excluded_sections_emits_one_entry_per_rule() -> None:
    config = _config_with_excluded_sections(
        [
            StoredExcludedSectionConf(target_id=(SID, "A"), sections=["jobs"]),
            StoredExcludedSectionConf(target_id=(SID, "B"), sections=["locks"]),
        ]
    )

    lines = _yaml_lines(config)

    assert lines.count("    - sections:") == 2
    assert "      sid: A" in lines
    assert "      sid: B" in lines


@pytest.mark.parametrize("excluded_sections", [None, []])
def test_excluded_sections_absent_when_no_rules(
    excluded_sections: list[StoredExcludedSectionConf] | None,
) -> None:
    lines = _yaml_lines(_config_with_excluded_sections(excluded_sections))
    assert not any("excluded_sections" in line for line in lines)


def test_excluded_sections_keeps_a_target_without_sections() -> None:
    # `sections` is optional in the ruleset, so the target survives with no list.
    config = _config_with_excluded_sections([StoredExcludedSectionConf(target_id=(SID, "XE"))])

    lines = _yaml_lines(config)

    assert "    - sid: XE" in lines
    assert not any(line.strip() == "sections:" for line in lines)
