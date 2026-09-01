#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Generic, Literal, NamedTuple, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict

from cmk.bakery.v2_unstable import (
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


class OraclePluginFile(NamedTuple):
    source: Path
    target: Path
    cached: bool = False


LIN_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.LINUX,
    [
        OraclePluginFile(
            source=Path("mk-oracle"),
            target=Path("libexec", "mk-oracle", "mk-oracle"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync"),
            target=Path("oracle_unified_sync"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async"),
            target=Path("oracle_unified_async"),
            cached=True,
        ),
    ],
)

WIN_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.WINDOWS,
    [
        OraclePluginFile(
            source=Path("mk-oracle.exe"),
            target=Path("libexec", "mk-oracle", "mk-oracle.exe"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync.ps1"),
            target=Path("oracle_unified_sync.ps1"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async.ps1"),
            target=Path("oracle_unified_async.ps1"),
            cached=True,
        ),
    ],
)

AIX_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.AIX,
    [
        OraclePluginFile(
            source=Path("mk-oracle.aix"),
            target=Path("libexec", "mk-oracle", "mk-oracle.aix"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync.aix"),
            target=Path("oracle_unified_sync.aix"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async.aix"),
            target=Path("oracle_unified_async.aix"),
            cached=True,
        ),
    ],
)

SOLARIS_ORACLE_FILES: tuple[OS, Sequence[OraclePluginFile]] = (
    OS.SOLARIS,
    [
        OraclePluginFile(
            source=Path("mk-oracle.solaris"),
            target=Path("libexec", "mk-oracle", "mk-oracle.solaris"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_sync.solaris"),
            target=Path("oracle_unified_sync.solaris"),
        ),
        OraclePluginFile(
            source=Path("oracle_unified_async.solaris"),
            target=Path("oracle_unified_async.solaris"),
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
        target=Path("oracle_unified_async_custom_metrics"),
        cached=True,
    ),
    OS.WINDOWS: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics.ps1"),
        target=Path("oracle_unified_async_custom_metrics.ps1"),
        cached=True,
    ),
    OS.AIX: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics.aix"),
        target=Path("oracle_unified_async_custom_metrics.aix"),
        cached=True,
    ),
    OS.SOLARIS: OraclePluginFile(
        source=Path("oracle_unified_async_custom_metrics.solaris"),
        target=Path("oracle_unified_async_custom_metrics.solaris"),
        cached=True,
    ),
}

GuiSectionOptions = Mapping[str, Literal["synchronous", "asynchronous", "disabled"]]


class OracleAuthType(StrEnum):
    STANDARD = "standard"
    WALLET = "wallet"


SecretT = TypeVar("SecretT", default=Secret)


class GuiAuthUserPasswordData(BaseModel, Generic[SecretT]):
    username: str | None
    password: SecretT | None


class GuiAsmAuthConf(BaseModel, Generic[SecretT]):
    username: str
    password: SecretT
    role: str | None = None


class GuiAuthConf(BaseModel, Generic[SecretT]):
    model_config = ConfigDict(use_enum_values=True)

    auth_type: tuple[OracleAuthType, GuiAuthUserPasswordData[SecretT] | None] | None = None
    role: str | None = None
    asm_auth: GuiAsmAuthConf[SecretT] | None = None


class GuiOracleIdentificationConf(BaseModel):
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None
    alias: str | None = None


class GuiConnectionConf(BaseModel):
    host: str | None = None
    port: int | None = None
    timeout: int | None = None
    tns_admin: str | None = None
    oracle_local_registry: str | None = None


class GuiDiscoveryConf(BaseModel):
    enabled: bool
    include: list[str] | None = None
    exclude: list[str] | None = None


class GuiOracleClientLibOptions(BaseModel):
    deploy_lib: bool = False
    use_host_client: (
        tuple[Literal["auto", "never", "always"], None] | tuple[Literal["custom"], str] | None
    ) = None


class GuiOracleSafeEntries(BaseModel):
    safe_entries: list[str] | None = None


class GuiAdditionalOptionsConf(BaseModel):
    max_connections: int | None = None
    max_queries: int | None = None
    ignore_db_name: bool | None = None
    oracle_client_library: GuiOracleClientLibOptions | None = None
    # `validate_permissions` is a CascadingSingleChoice in the ruleset, so its value is a bare
    # tuple, and the field name must match the ruleset key for Pydantic to bind it.
    validate_permissions: (
        tuple[Literal["enabled"], GuiOracleSafeEntries | None]
        | tuple[Literal["disabled"], None]
        | None
    ) = None


class GuiExcludedSectionConf(BaseModel):
    target_id: tuple[Literal["alias", "descriptor", "sid"], GuiOracleIdentificationConf]
    sections: list[str] | None = None


class GuiMainConf(BaseModel, Generic[SecretT]):
    auth: GuiAuthConf[SecretT]
    connection: GuiConnectionConf
    cache_age: int | None = None
    custom_metrics_cache_age: int | None = None
    discovery: GuiDiscoveryConf | None = None
    sections: GuiSectionOptions | None = None
    excluded_sections: list[GuiExcludedSectionConf] | None = None

    def get_active_cache_age(self) -> int:
        """Return cache age in seconds, default is 600 seconds: must be in sync with agent plugin"""
        return self.cache_age or 600

    def get_active_custom_metrics_cache_age(self) -> int:
        """Return metrics cache age in seconds, default is 600 seconds: must be in sync with agent plugin"""
        return self.custom_metrics_cache_age or 600


class GuiInstanceAdditionalOptionsConf(BaseModel):
    ignore_db_name: bool | None = None
    oracle_client_library: GuiOracleClientLibOptions | None = None


class GuiInstanceConf(BaseModel, Generic[SecretT]):
    oracle_id: tuple[Literal["alias", "descriptor", "sid"], GuiOracleIdentificationConf]
    auth: GuiAuthConf[SecretT] | None = None
    connection: GuiConnectionConf | None = None
    piggyback_host: str | None = None


class GuiConfig(BaseModel, Generic[SecretT]):
    deploy: tuple[Literal["deploy"] | Literal["do_not_deploy"], None]
    # `options` is a top-level GUI section; it is baked into `oracle.main.options`.
    options: GuiAdditionalOptionsConf | None = None
    main: GuiMainConf[SecretT]
    instances: list[GuiInstanceConf[SecretT]] | None = None


class OracleAdditionalOptions(BaseModel):
    max_connections: int | None = None
    max_queries: int | None = None
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
    username: str | None = None
    password: str | None = None
    role: str | None = None
    asm_username: str | None = None
    asm_password: str | None = None
    asm_role: str | None = None
    type: OracleAuthType | None = None

    class Config:
        use_enum_values = True


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


def get_oracle_plugin_files(confm: GuiConfig) -> FileGenerator:
    if confm.deploy[0] == "do_not_deploy":
        return

    config_lines = list(_get_oracle_yaml_lines(confm))
    cache_age = confm.main.get_active_cache_age()
    custom_metrics_cache_age = confm.main.get_active_custom_metrics_cache_age()
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


def _get_oracle_yaml_lines(config: GuiConfig) -> Iterable[str]:
    result = {"oracle": OracleConfig(main=_get_oracle_dict(config)).model_dump(exclude_none=True)}
    yield "---"
    yield from yaml.dump(result).splitlines()


def _get_oracle_dict(config: GuiConfig) -> OracleMain:
    main_config = config.main
    instances_config = config.instances

    if not (auth := _get_oracle_authentication(main_config.auth)):
        raise ValueError("Authentication details must be provided in main configuration.")

    return OracleMain(
        authentication=auth,
        connection=_get_oracle_connection(main_config.connection),
        options=_get_oracle_additional_options(config.options),
        discovery=_get_oracle_discovery(main_config.discovery),
        sections=_get_oracle_sections(main_config.sections),
        instances=_get_oracle_instances(instances_config),
        cache_age=main_config.get_active_cache_age(),
        custom_metrics_cache_age=main_config.get_active_custom_metrics_cache_age(),
        excluded_sections=_get_oracle_excluded_sections(main_config.excluded_sections),
    )


def _get_oracle_authentication(auth_config: GuiAuthConf | None) -> OracleAuth | None:
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
        case (OracleAuthType.STANDARD.value, GuiAuthUserPasswordData() as auth_data):
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
    conn: GuiConnectionConf | None, *, include_tns_admin: bool = True
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
    options: GuiAdditionalOptionsConf | None,
) -> OracleAdditionalOptions | None:
    if options is None:
        return None
    if (
        (
            options.oracle_client_library is None
            or options.oracle_client_library.use_host_client is None
        )
        and options.ignore_db_name is None
        and options.max_connections is None
        and options.max_queries is None
        and options.validate_permissions is None
    ):
        return None

    use_host_client: str | None = None
    if options.oracle_client_library is not None:
        match options.oracle_client_library.use_host_client:
            case (("auto" | "never" | "always") as predefined, None):
                use_host_client = predefined
            case ("custom", custom_path):
                use_host_client = str(custom_path)
            case None:
                pass
    permissions_check: bool | None = None
    permissions_safe_entries: list[str] | None = None
    match options.validate_permissions:
        case ("enabled", GuiOracleSafeEntries(safe_entries=entries)):
            permissions_check = True
            permissions_safe_entries = entries
        case ("disabled", None):
            permissions_check = False
        case None:
            pass

    return OracleAdditionalOptions(
        max_connections=options.max_connections,
        max_queries=options.max_queries,
        ignore_db_name=int(options.ignore_db_name) if options.ignore_db_name is not None else None,
        use_host_client=use_host_client,
        permissions_check=permissions_check,
        permissions_safe_entries=permissions_safe_entries,
    )


def _get_oracle_discovery(discovery: GuiDiscoveryConf | None) -> OracleDiscovery | None:
    if discovery is None:
        return None

    return OracleDiscovery(
        detect=discovery.enabled,
        include=discovery.include or None,
        exclude=discovery.exclude or None,
    )


def _get_oracle_sections(
    sections: GuiSectionOptions | None,
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


def _get_oracle_instances(instances: list[GuiInstanceConf] | None) -> list[OracleInstance] | None:
    if instances is None:
        return None

    result: list[OracleInstance] = []
    for instance in instances:
        (_name, oracle_id) = instance.oracle_id
        if (
            oracle_id.service_name is None
            and oracle_id.instance_name is None
            and oracle_id.sid is None
            and oracle_id.alias is None
            and instance.auth is None
            and instance.connection is None
        ):
            continue
        oracle_instance = OracleInstance(
            service_name=oracle_id.service_name,
            instance_name=oracle_id.instance_name,
            sid=oracle_id.sid,
            alias=oracle_id.alias,
            authentication=_get_oracle_authentication(instance.auth),
            connection=_get_oracle_connection(instance.connection, include_tns_admin=False),
            piggyback=OraclePiggyback(hostname=instance.piggyback_host)
            if instance.piggyback_host
            else None,
        )
        result.append(oracle_instance)
    return result


def _get_oracle_excluded_sections(
    rules: list[GuiExcludedSectionConf] | None,
) -> list[OracleExcludedSection] | None:
    if not rules:
        return None

    result: list[OracleExcludedSection] = []
    for rule in rules:
        (_name, target_id) = rule.target_id
        if (
            target_id.service_name is None
            and target_id.instance_name is None
            and target_id.sid is None
            and target_id.alias is None
        ):
            continue
        excluded = OracleExcludedSection(
            service_name=target_id.service_name,
            instance_name=target_id.instance_name,
            sid=target_id.sid,
            alias=target_id.alias,
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


def get_oracle_plugin_scriplets(confm: GuiConfig) -> Iterable[Scriptlet]:
    if confm.deploy[0] == "do_not_deploy":
        return

    arm_warning_lines = _get_arm_warning_lines()

    yield Scriptlet(step=DebStep.POSTINST, lines=arm_warning_lines)
    yield Scriptlet(step=RpmStep.POST, lines=arm_warning_lines)


bakery_plugin_oracle = BakeryPlugin(
    name="mk_oracle_unified",
    parameter_parser=GuiConfig.model_validate,
    default_parameters=None,
    files_function=get_oracle_plugin_files,
    scriptlets_function=get_oracle_plugin_scriplets,
)
