#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal, NamedTuple

import yaml
from pydantic import BaseModel

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
            target=Path("packages", "mk-oracle", "mk-oracle"),
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
            target=Path("packages", "mk-oracle", "mk-oracle.exe"),
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

GuiSectionOptions = Mapping[str, Literal["synchronous", "asynchronous", "disabled"]]


class OracleAuthType(StrEnum):
    STANDARD = "standard"
    WALLET = "wallet"


class GuiAuthUserPasswordData(BaseModel):
    username: str | None
    password: Secret | None


class GuiAuthConf(BaseModel):
    auth_type: tuple[OracleAuthType, GuiAuthUserPasswordData | None] | None = None
    role: str | None = None

    class Config:
        use_enum_values = True


class GuiOracleIdentificationConf(BaseModel):
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None
    alias: str | None = None


class GuiConnectionConf(BaseModel):
    host: str = "localhost"
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


class GuiAdditionalOptionsConf(BaseModel):
    max_connections: int | None = None
    max_queries: int | None = None
    ignore_db_name: bool | None = None
    oracle_client_library: GuiOracleClientLibOptions | None = None


class GuiMainConf(BaseModel):
    auth: GuiAuthConf
    connection: GuiConnectionConf
    options: GuiAdditionalOptionsConf | None = None
    cache_age: int | None = None
    discovery: GuiDiscoveryConf | None = None
    sections: GuiSectionOptions | None = None

    def get_active_cache_age(self) -> int:
        """Return cache age in seconds, default is 600 seconds: must be in sync with agent plugin"""
        return self.cache_age or 600


class GuiInstanceAdditionalOptionsConf(BaseModel):
    ignore_db_name: bool | None = None
    oracle_client_library: GuiOracleClientLibOptions | None = None


class GuiInstanceConf(BaseModel):
    oracle_id: GuiOracleIdentificationConf
    auth: GuiAuthConf | None = None
    connection: GuiConnectionConf | None = None


class GuiConfig(BaseModel):
    deploy: tuple[Literal["deploy"] | Literal["do_not_deploy"], None]
    main: GuiMainConf
    instances: list[GuiInstanceConf] | None = None


class OracleAdditionalOptions(BaseModel):
    max_connections: int | None = None
    max_queries: int | None = None
    ignore_db_name: int | None = None
    use_host_client: str | None = None


class OracleDiscovery(BaseModel):
    enabled: bool
    include: list[str] | None = None
    exclude: list[str] | None = None


class OracleSection(BaseModel):
    is_async: bool | None = None


class OracleAuth(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None
    type: OracleAuthType | None = None

    class Config:
        use_enum_values = True


class OracleConnection(BaseModel):
    hostname: str
    port: int | None = None
    timeout: int | None = None
    tns_admin: str | None = None
    oracle_local_registry: str | None = None


class OracleInstanceAdditionalOptions(BaseModel):
    ignore_db_name: int | None = None
    use_host_client: str | None = None


class OracleInstance(BaseModel):
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None
    alias: str | None = None
    authentication: OracleAuth | None = None
    connection: OracleConnection | None = None


class OracleMain(BaseModel):
    authentication: OracleAuth
    connection: OracleConnection | None
    options: OracleAdditionalOptions | None = None
    cache_age: int | None = None
    discovery: OracleDiscovery | None = None
    sections: Sequence[Mapping[str, OracleSection]] | None = None
    instances: list[OracleInstance] | None = None


class OracleConfig(BaseModel):
    main: OracleMain


def get_oracle_plugin_files(confm: GuiConfig) -> FileGenerator:
    if confm.deploy[0] == "do_not_deploy":
        return

    config_lines = list(_get_oracle_yaml_lines(confm))

    for base_os, files in (LIN_ORACLE_FILES, WIN_ORACLE_FILES):
        for file in files:
            yield Plugin(
                base_os=base_os,
                target=file.target,
                source=file.source,
                interval=confm.main.get_active_cache_age() if file.cached else None,
            )

        yield PluginConfig(
            base_os=base_os,
            lines=config_lines,
            target=Path("oracle.yml"),
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
        options=_get_oracle_additional_options(main_config.options),
        discovery=_get_oracle_discovery(main_config.discovery),
        sections=_get_oracle_sections(main_config.sections),
        instances=_get_oracle_instances(instances_config),
        cache_age=main_config.get_active_cache_age(),
    )


def _get_oracle_authentication(auth_config: GuiAuthConf | None) -> OracleAuth | None:
    if auth_config is None:
        return None
    if auth_config.auth_type is None and auth_config.role:
        return OracleAuth(role=auth_config.role)
    match auth_config.auth_type:
        case (OracleAuthType.WALLET.value, _):
            return OracleAuth(type=OracleAuthType.WALLET, role=auth_config.role)
        case (OracleAuthType.STANDARD.value, GuiAuthUserPasswordData() as auth_data):
            return OracleAuth(
                username=auth_data.username,
                password=auth_data.password.revealed if auth_data.password else None,
                type=OracleAuthType.STANDARD,
                role=auth_config.role,
            )
        case _:
            raise ValueError(f"Unsupported authentication type: {auth_config.auth_type}")


def _get_oracle_connection(conn: GuiConnectionConf | None) -> OracleConnection | None:
    if conn is None:
        return None

    return OracleConnection(
        hostname=conn.host,
        port=conn.port,
        timeout=conn.timeout,
        tns_admin=conn.tns_admin,
        oracle_local_registry=conn.oracle_local_registry,
    )


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

    return OracleAdditionalOptions(
        max_connections=options.max_connections,
        max_queries=options.max_queries,
        ignore_db_name=int(options.ignore_db_name) if options.ignore_db_name is not None else None,
        use_host_client=use_host_client,
    )


def _get_oracle_discovery(discovery: GuiDiscoveryConf | None) -> OracleDiscovery | None:
    if discovery is None:
        return None

    return OracleDiscovery(
        enabled=discovery.enabled,
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
        oracle_id = instance.oracle_id
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
            connection=_get_oracle_connection(instance.connection),
        )
        result.append(oracle_instance)
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
