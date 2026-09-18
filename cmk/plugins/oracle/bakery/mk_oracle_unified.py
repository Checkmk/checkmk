#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

import yaml
from pydantic import BaseModel, ConfigDict

from cmk.bakery.v2 import (
    BakeryPlugin,
    DebStep,
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
    RpmStep,
    Scriptlet,
    Secret,
)
from cmk.plugins.oracle.lib.unified_config import (
    StoredAdditionalOptionsConf,
    StoredAsmAuthConf,
    StoredAuthConf,
    StoredAuthUserPasswordData,
    StoredConfig,
    StoredConnectionConf,
    StoredDiscoveryConf,
    StoredExcludedSectionConf,
    StoredInstanceConf,
    StoredOracleId,
    StoredOracleSafeEntries,
    StoredSectionOptions,
)


class OraclePluginFile(NamedTuple):
    source: Path
    target: Path
    cached: bool = False


LIN_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.LINUX,
    [
        OraclePluginFile(
            source=Path("mk-oracle"),
            target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync"),
            target=Path("mk-oracle-v2_sync"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async"),
            target=Path("mk-oracle-v2_async"),
            cached=True,
        ),
    ],
)

WIN_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.WINDOWS,
    [
        OraclePluginFile(
            source=Path("mk-oracle.exe"),
            target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2.exe"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync.ps1"),
            target=Path("mk-oracle-v2_sync.ps1"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async.ps1"),
            target=Path("mk-oracle-v2_async.ps1"),
            cached=True,
        ),
    ],
)

AIX_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.AIX,
    [
        OraclePluginFile(
            source=Path("mk-oracle.aix"),
            target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2.aix"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync.aix"),
            target=Path("mk-oracle-v2_sync.aix"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async.aix"),
            target=Path("mk-oracle-v2_async.aix"),
            cached=True,
        ),
    ],
)

SOLARIS_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.SOLARIS,
    [
        OraclePluginFile(
            source=Path("mk-oracle.solaris"),
            target=Path("libexec", "mk-oracle-v2", "mk-oracle-v2.solaris"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync.solaris"),
            target=Path("mk-oracle-v2_sync.solaris"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async.solaris"),
            target=Path("mk-oracle-v2_async.solaris"),
            cached=True,
        ),
    ],
)

OS_ORACLE_FILES: Sequence[tuple[OS, Sequence[OraclePluginFile]]] = (
    LIN_ORACLE_FILES,
    WIN_ORACLE_FILES,
    AIX_ORACLE_FILES,
    SOLARIS_ORACLE_FILES,
)

CUSTOM_METRICS_ASYNC_FILES: Mapping[OS, OraclePluginFile] = {
    OS.LINUX: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics"),
        target=Path("mk-oracle-v2_async_custom_metrics"),
        cached=True,
    ),
    OS.WINDOWS: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics.ps1"),
        target=Path("mk-oracle-v2_async_custom_metrics.ps1"),
        cached=True,
    ),
    OS.AIX: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics.aix"),
        target=Path("mk-oracle-v2_async_custom_metrics.aix"),
        cached=True,
    ),
    OS.SOLARIS: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics.solaris"),
        target=Path("mk-oracle-v2_async_custom_metrics.solaris"),
        cached=True,
    ),
}


class OracleAuthType(StrEnum):
    STANDARD = "standard"
    WALLET = "wallet"


# The rule value as the bakery sees it: the backend has replaced every password
# store reference with a Secret by now.
BakedAuthUserPasswordData = StoredAuthUserPasswordData[Secret]
BakedAsmAuthConf = StoredAsmAuthConf[Secret]
BakedAuthConf = StoredAuthConf[Secret]
BakedInstanceConf = StoredInstanceConf[Secret]
BakedConfig = StoredConfig[Secret]


class OracleAdditionalOptions(BaseModel):
    max_connections: int | None = None
    ignore_db_name: int | None = None
    use_host_client: str | None = None
    permissions_check: bool | None = None
    permissions_safe_entries: list[str] | None = None


class OracleDiscovery(BaseModel):
    detect: bool
    include: list[str] | None = None
    exclude: list[str] | None = None


class OracleSection(BaseModel):
    is_async: bool | None = None


class OracleAuth(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    username: str | None = None
    password: str | None = None
    role: str | None = None
    asm_username: str | None = None
    asm_password: str | None = None
    asm_role: str | None = None
    type: OracleAuthType | None = None


class OracleConnection(BaseModel):
    # Left out when the rule does not name a host, so that the plug-in applies
    # its own default. That default is not always localhost: on a node running
    # Grid Infrastructure the plug-in connects to the node itself.
    hostname: str | None = None
    port: int | None = None
    timeout: int | None = None
    tns_admin: str | None = None
    oracle_local_registry: str | None = None


class OracleInstanceAdditionalOptions(BaseModel):
    ignore_db_name: int | None = None
    use_host_client: str | None = None


class OraclePiggyback(BaseModel):
    hostname: str


class OracleInstance(BaseModel):
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None
    alias: str | None = None
    authentication: OracleAuth | None = None
    connection: OracleConnection | None = None
    piggyback: OraclePiggyback | None = None


class OracleExcludedSection(BaseModel):
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None
    alias: str | None = None
    sections: list[str] | None = None


class OracleMain(BaseModel):
    authentication: OracleAuth
    connection: OracleConnection | None
    options: OracleAdditionalOptions | None = None
    cache_age: int | None = None
    custom_metrics_cache_age: int | None = None
    discovery: OracleDiscovery | None = None
    sections: Sequence[Mapping[str, OracleSection]] | None = None
    instances: list[OracleInstance] | None = None
    excluded_sections: list[OracleExcludedSection] | None = None


class OracleConfig(BaseModel):
    main: OracleMain


def get_oracle_plugin_files(confm: BakedConfig) -> FileGenerator:
    if confm.deploy_rev2 == "do_not_deploy":
        return

    config_lines = list(_get_oracle_yaml_lines(confm))
    cache_age = confm.get_active_cache_age()
    custom_metrics_cache_age = confm.get_active_custom_metrics_cache_age()
    deploy_custom_metrics = cache_age != custom_metrics_cache_age

    for base_os, files in OS_ORACLE_FILES:
        for file in files:
            yield Plugin(
                base_os=base_os,
                target=file.target,
                source=file.source,
                interval=cache_age if file.cached else None,
            )

        if deploy_custom_metrics:
            cm_file = CUSTOM_METRICS_ASYNC_FILES[base_os]
            yield Plugin(
                base_os=base_os,
                target=cm_file.target,
                source=cm_file.source,
                interval=custom_metrics_cache_age,
            )

        yield PluginConfig(
            base_os=base_os,
            lines=config_lines,
            target=Path("mk-oracle.yml"),
        )


def _get_oracle_yaml_lines(config: BakedConfig) -> Iterable[str]:
    result = {"oracle": OracleConfig(main=_get_oracle_dict(config)).model_dump(exclude_none=True)}
    yield "---"
    yield from yaml.dump(result).splitlines()


def _get_oracle_dict(config: BakedConfig) -> OracleMain:
    if not (auth := _get_oracle_authentication(config.auth)):
        raise ValueError("Authentication details must be provided.")

    return OracleMain(
        authentication=auth,
        connection=_get_oracle_connection(config.connection),
        options=_get_oracle_additional_options(config.options),
        discovery=_get_oracle_discovery(config.discovery),
        sections=_get_oracle_sections(config.sections),
        instances=_get_oracle_instances(config.instances_rev2),
        cache_age=config.get_active_cache_age(),
        custom_metrics_cache_age=config.get_active_custom_metrics_cache_age(),
        excluded_sections=_get_oracle_excluded_sections(config.excluded_sections),
    )


def _get_oracle_authentication(auth_config: BakedAuthConf | None) -> OracleAuth | None:
    if auth_config is None:
        return None

    asm_username = auth_config.asm_auth.username if auth_config.asm_auth else None
    asm_password = auth_config.asm_auth.password.revealed if auth_config.asm_auth else None
    asm_role = auth_config.asm_auth.role if auth_config.asm_auth else None
    username: str | None = None
    password: str | None = None
    auth_type: OracleAuthType | None = None

    match auth_config.auth_type:
        case None:
            if not auth_config.role and not auth_config.asm_auth:
                return None
        case (OracleAuthType.WALLET.value, _):
            auth_type = OracleAuthType.WALLET
        case (OracleAuthType.STANDARD.value, StoredAuthUserPasswordData() as auth_data):
            username = auth_data.username
            password = auth_data.password.revealed if auth_data.password else None
            auth_type = OracleAuthType.STANDARD
        case _:
            raise ValueError(f"Unsupported authentication type: {auth_config.auth_type}")
    return OracleAuth(
        username=username,
        password=password,
        type=auth_type,
        role=auth_config.role,
        asm_role=asm_role,
        asm_username=asm_username,
        asm_password=asm_password,
    )


def _get_oracle_connection(
    conn: StoredConnectionConf | None, *, include_tns_admin: bool = True
) -> OracleConnection | None:
    if conn is None:
        return None

    connection = OracleConnection(
        hostname=conn.host,
        port=conn.port,
        timeout=conn.timeout,
        # tns_admin applies to the main connection only; per-instance it is
        # reserved and ignored by the plug-in, so it is never baked.
        tns_admin=conn.tns_admin if include_tns_admin else None,
        oracle_local_registry=conn.oracle_local_registry,
    )
    # An entirely empty block would say nothing that the plug-in does not
    # already default to.
    if not connection.model_dump(exclude_none=True):
        return None
    return connection


def _get_oracle_additional_options(
    options: StoredAdditionalOptionsConf | None,
) -> OracleAdditionalOptions | None:
    if options is None:
        return None
    if (
        options.use_host_client is None
        and options.ignore_db_name is None
        and options.max_connections is None
        and options.validate_permissions is None
    ):
        return None

    use_host_client: str | None = None
    match options.use_host_client:
        case (("auto" | "never" | "always") as predefined, _):
            use_host_client = predefined
        case ("custom", custom_path):
            use_host_client = custom_path
        case None:
            pass
    permissions_check: bool | None = None
    permissions_safe_entries: list[str] | None = None
    match options.validate_permissions:  # type: ignore[exhaustive-match]
        case ("enabled", StoredOracleSafeEntries(safe_entries=entries)):
            permissions_check = True
            permissions_safe_entries = entries
        case ("disabled", None):
            permissions_check = False
        case None:
            pass

    return OracleAdditionalOptions(
        max_connections=options.max_connections,
        ignore_db_name=int(options.ignore_db_name) if options.ignore_db_name is not None else None,
        use_host_client=use_host_client,
        permissions_check=permissions_check,
        permissions_safe_entries=permissions_safe_entries,
    )


def _get_oracle_discovery(discovery: StoredDiscoveryConf | None) -> OracleDiscovery | None:
    if discovery is None:
        return None

    return OracleDiscovery(
        detect=discovery.enabled,
        include=discovery.include or None,
        exclude=discovery.exclude or None,
    )


def _get_oracle_sections(
    sections: StoredSectionOptions | None,
) -> Sequence[Mapping[str, OracleSection]] | None:
    if sections is None:
        return None

    result: list[dict[str, OracleSection]] = []
    for section_name, mode in sections.items():
        match mode:
            case "synchronous":
                result.append({section_name: OracleSection(is_async=False)})
            case "asynchronous":
                result.append({section_name: OracleSection(is_async=True)})
            case "disabled":
                continue
    return result


class _Identification(NamedTuple):
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None
    alias: str | None = None


def _identification(oracle_id: StoredOracleId) -> _Identification:
    match oracle_id:
        case ("alias", alias):
            return _Identification(alias=alias)
        case ("sid", sid):
            return _Identification(sid=sid)
        case ("descriptor", descriptor):
            return _Identification(
                service_name=descriptor.service_name,
                instance_name=descriptor.instance_name,
                sid=descriptor.sid,
            )


def _get_oracle_instances(instances: list[BakedInstanceConf] | None) -> list[OracleInstance] | None:
    if instances is None:
        return None

    result: list[OracleInstance] = []
    for instance in instances:
        identification = _identification(instance.oracle_id)
        oracle_instance = OracleInstance(
            service_name=identification.service_name,
            instance_name=identification.instance_name,
            sid=identification.sid,
            alias=identification.alias,
            authentication=_get_oracle_authentication(instance.auth),
            connection=_get_oracle_connection(instance.connection, include_tns_admin=False),
            piggyback=OraclePiggyback(hostname=instance.piggyback_host)
            if instance.piggyback_host
            else None,
        )
        result.append(oracle_instance)
    return result


def _get_oracle_excluded_sections(
    rules: list[StoredExcludedSectionConf] | None,
) -> list[OracleExcludedSection] | None:
    if not rules:
        return None

    result: list[OracleExcludedSection] = []
    for rule in rules:
        identification = _identification(rule.target_id)
        excluded = OracleExcludedSection(
            service_name=identification.service_name,
            instance_name=identification.instance_name,
            sid=identification.sid,
            alias=identification.alias,
            sections=rule.sections,
        )
        result.append(excluded)
    return result


def _get_arm_warning_lines() -> list[str]:
    """Generate shell script lines to check architecture and warn if ARM."""
    return [
        "# Check if system is ARM architecture",
        "ARCH=$(uname -m)",
        'case "$ARCH" in',
        "    aarch64|arm64|armv*)",
        '        echo "WARNING: mk_oracle_unified plugin is not supported on ARM systems ($ARCH)." 1>&2',
        '        echo "The plugin may not function correctly on this architecture." 1>&2',
        "        ;;",
        "esac",
    ]


def get_oracle_plugin_scriplets(confm: BakedConfig) -> Iterable[Scriptlet]:
    if confm.deploy_rev2 == "do_not_deploy":
        return

    arm_warning_lines = _get_arm_warning_lines()

    yield Scriptlet(step=DebStep.POSTINST, lines=arm_warning_lines)
    yield Scriptlet(step=RpmStep.POST, lines=arm_warning_lines)


bakery_plugin_oracle = BakeryPlugin(
    name="mk_oracle_unified",
    parameter_parser=BakedConfig.model_validate,
    default_parameters=None,
    files_function=get_oracle_plugin_files,
    scriptlets_function=get_oracle_plugin_scriplets,
)
