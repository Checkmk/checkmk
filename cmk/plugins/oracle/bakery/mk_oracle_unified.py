#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal, NamedTuple, NotRequired, TypedDict

import yaml
from pydantic import BaseModel

from cmk.bakery.v2_unstable import (
    BakeryPlugin,
    FileGenerator,
    OS,
    Plugin,
    PluginConfig,
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


class GuiAuthUserPasswordData(BaseModel):
    username: str
    password: Secret
    role: str | None = None


class GuiInstanceAuthUserPasswordData(BaseModel):
    username: str | None = None
    password: Secret | None = None
    role: str | None = None


class GuiOracleIdentificationConf(BaseModel):
    service_name: str
    instance_name: str | None = None


class GuiConnectionConf(BaseModel):
    host: str = "localhost"
    port: int | None = None
    timeout: int | None = None
    tns_admin: str | None = None
    oracle_local_registry: str | None = None
    oracle_id: GuiOracleIdentificationConf | None = None


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
    auth: tuple[Literal["standard"], GuiAuthUserPasswordData]
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
    service_name: str | None
    instance_name: str | None
    auth: tuple[Literal["standard"], GuiInstanceAuthUserPasswordData] | None = None
    connection: GuiConnectionConf | None = None


class GuiConfig(BaseModel):
    deploy: tuple[Literal["deploy"] | Literal["do_not_deploy"], None]
    main: GuiMainConf
    instances: list[GuiInstanceConf] | None = None


class OracleAdditionalOptions(TypedDict):
    max_connections: NotRequired[int]
    max_queries: NotRequired[int]
    ignore_db_name: NotRequired[int]
    use_host_client: NotRequired[str]


class OracleDiscovery(TypedDict):
    enabled: bool
    include: NotRequired[list[str]]
    exclude: NotRequired[list[str]]


class OracleSection(TypedDict):
    is_async: NotRequired[bool]


class OracleAuth(TypedDict):
    username: str
    password: str
    role: NotRequired[str]
    type: NotRequired[str]


class OracleConnection(TypedDict):
    hostname: str
    port: NotRequired[int]
    timeout: NotRequired[int]
    tns_admin: NotRequired[str]
    oracle_local_registry: NotRequired[str]
    service_name: NotRequired[str]
    instance: NotRequired[str]


class OracleInstanceAuth(TypedDict):
    username: NotRequired[str]
    password: NotRequired[str]
    role: NotRequired[str]
    type: NotRequired[str]


class OracleInstanceAdditionalOptions(TypedDict):
    ignore_db_name: NotRequired[int]
    use_host_client: NotRequired[str]


class OracleInstance(TypedDict):
    service_name: NotRequired[str]
    instance_name: NotRequired[str]
    authentication: NotRequired[OracleInstanceAuth]
    connection: NotRequired[OracleConnection]


class OracleMain(TypedDict):
    authentication: OracleAuth
    connection: OracleConnection
    options: NotRequired[OracleAdditionalOptions]
    cache_age: NotRequired[int]
    discovery: NotRequired[OracleDiscovery]
    sections: NotRequired[Sequence[Mapping[str, OracleSection]]]
    instances: NotRequired[list[OracleInstance]]


class OracleConfig(TypedDict):
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
    result = {"oracle": OracleConfig(main=_get_oracle_dict(config))}
    yield "---"
    yield from yaml.dump(result).splitlines()


def _get_oracle_dict(config: GuiConfig) -> OracleMain:
    main_config = config.main
    instances_config = config.instances

    oracle_main = OracleMain(
        authentication=_get_oracle_authentication(main_config.auth),
        connection=_get_oracle_connection(main_config.connection),
    )
    if main_config.options and (
        additional_options := _get_oracle_additional_options(main_config.options)
    ):
        oracle_main["options"] = additional_options
    if main_config.discovery:
        oracle_main["discovery"] = _get_oracle_discovery(main_config.discovery)
    if main_config.sections:
        oracle_main["sections"] = _get_oracle_sections(main_config.sections)
    if instances_config:
        oracle_main["instances"] = _get_oracle_instances(instances_config)
    oracle_main["cache_age"] = main_config.get_active_cache_age()
    return oracle_main


def _get_oracle_authentication(auth_config: tuple[str, GuiAuthUserPasswordData]) -> OracleAuth:
    auth_type = auth_config[0]
    auth_data = auth_config[1]
    auth = OracleAuth(username=auth_data.username, password=auth_data.password.revealed)
    if role := auth_data.role:
        auth["role"] = role
    auth["type"] = auth_type
    return auth


def _get_oracle_connection(conn: GuiConnectionConf) -> OracleConnection:
    connection = OracleConnection(hostname=conn.host)
    if hostname := conn.host:
        connection["hostname"] = hostname
    if port := conn.port:
        connection["port"] = port
    if timeout := conn.timeout:
        connection["timeout"] = timeout
    if tns_admin := conn.tns_admin:
        connection["tns_admin"] = tns_admin
    if oracle_local_registry := conn.oracle_local_registry:
        connection["oracle_local_registry"] = oracle_local_registry
    if oracle_id := conn.oracle_id:
        connection["service_name"] = oracle_id.service_name
        if oracle_id.instance_name:
            connection["instance"] = oracle_id.instance_name
    return connection


def _get_oracle_additional_options(options: GuiAdditionalOptionsConf) -> OracleAdditionalOptions:
    result: OracleAdditionalOptions = {}
    if options.max_connections is not None:
        result["max_connections"] = options.max_connections
    if options.max_queries is not None:
        result["max_queries"] = options.max_queries
    if options.ignore_db_name is not None:
        result["ignore_db_name"] = int(options.ignore_db_name)
    if options.oracle_client_library is not None:
        match options.oracle_client_library.use_host_client:
            case (("auto" | "never" | "always") as predefined, None):
                result["use_host_client"] = predefined
            case ("custom", custom_path):
                result["use_host_client"] = str(custom_path)
            case None:
                pass
    return result


def _get_oracle_instance_additional_options(
    options: GuiInstanceAdditionalOptionsConf,
) -> OracleInstanceAdditionalOptions:
    result: OracleInstanceAdditionalOptions = {}
    if options.ignore_db_name is not None:
        result["ignore_db_name"] = int(options.ignore_db_name)
    if options.oracle_client_library is not None:
        match options.oracle_client_library.use_host_client:
            case (("auto" | "never" | "always") as predefined, None):
                result["use_host_client"] = predefined
            case ("custom", custom_path):
                result["use_host_client"] = str(custom_path)
            case None:
                pass
    return result


def _get_oracle_discovery(discovery: GuiDiscoveryConf) -> OracleDiscovery:
    result: OracleDiscovery = {"enabled": discovery.enabled}
    if discovery.include:
        result["include"] = discovery.include
    if discovery.exclude:
        result["exclude"] = discovery.exclude
    return result


def _get_oracle_sections(
    sections: GuiSectionOptions,
) -> Sequence[Mapping[str, OracleSection]]:
    result: list[dict[str, OracleSection]] = []
    for section_name, mode in sections.items():
        oracle_section: OracleSection = {}
        match mode:
            case "synchronous":
                oracle_section["is_async"] = False
            case "asynchronous":
                oracle_section["is_async"] = True
            case "disabled":
                continue
        result.append({section_name: oracle_section})
    return result


def _get_oracle_instance_authentication(
    auth_config: tuple[str, GuiInstanceAuthUserPasswordData],
) -> OracleInstanceAuth:
    auth_data = auth_config[1]
    auth = OracleInstanceAuth()
    if username := auth_data.username:
        auth["username"] = username
    if password := auth_data.password:
        auth["password"] = password.revealed
    if role := auth_data.role:
        auth["role"] = role
    if auth_type := auth_config[0]:
        auth["type"] = auth_type
    return auth


def _get_oracle_instances(instances: list[GuiInstanceConf]) -> list[OracleInstance]:
    result: list[OracleInstance] = []
    for instance in instances:
        if (
            not instance.service_name
            and not instance.instance_name
            and instance.auth is None
            and instance.connection is None
        ):
            continue
        inst_dict: OracleInstance = {}
        if instance.service_name:
            inst_dict["service_name"] = instance.service_name
        if instance.instance_name:
            inst_dict["instance_name"] = instance.instance_name
        if instance.auth:
            inst_dict["authentication"] = _get_oracle_instance_authentication(instance.auth)
        if instance.connection:
            inst_dict["connection"] = _get_oracle_connection(instance.connection)
        result.append(inst_dict)
    return result


bakery_plugin_oracle = BakeryPlugin(
    name="mk_oracle_unified",
    parameter_parser=GuiConfig.model_validate,
    default_parameters=None,
    files_function=get_oracle_plugin_files,
)
