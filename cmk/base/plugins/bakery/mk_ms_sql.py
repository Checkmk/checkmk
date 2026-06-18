#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final, Literal, NamedTuple, NotRequired, TypedDict

import yaml

from .bakery_api.v1 import FileGenerator, OS, password_store, Plugin, PluginConfig, register

GuiAuth = str | tuple[str, tuple[str, password_store.PasswordId | str]]
# must be identical to the values in the GUI
_SYSTEM_DATABASES: Final[tuple[str, str, str, str]] = ("model", "master", "msdb", "tempdb")


class MsSqlSetup(NamedTuple):
    base_os: OS
    plugin_source: Path
    plugin_target: Path
    config_name: str = "mk-sql.yml"


OS_Setups: Sequence[MsSqlSetup] = [
    MsSqlSetup(
        base_os=OS.LINUX,
        plugin_source=Path("..", "linux", "mk-sql"),  # agents/linux/
        plugin_target=Path("mk-sql"),
    ),
    MsSqlSetup(
        base_os=OS.WINDOWS,
        plugin_source=Path("..", "mk-sql.exe"),  # agents/windows
        plugin_target=Path("mk-sql.exe"),
    ),
]


class GuiTls(TypedDict):
    client_certificate: str


class GuiConn(TypedDict):
    hostname: str
    fail_over_partner: str
    port: int
    timeout: int
    trust_server_certificate: bool
    tls: GuiTls
    backend: str
    exclude_databases: Sequence[str]


_SectionType = Literal["sync", "async", "disabled"] | None


GuiIncludeExclude = str | tuple[str, list[str]]


GuiDiscovery = tuple[bool, GuiIncludeExclude]


class GuiOptions(TypedDict):
    max_connections: NotRequired[int]
    ignore_inactive_local_instances: NotRequired[bool]


class GuiPiggyback(TypedDict):
    hostname: str
    sections: dict[str, _SectionType]
    cache_age: int


class GuiInstance(TypedDict):
    sid: str
    auth: GuiAuth
    conn: GuiConn
    alias: str
    piggyback: GuiPiggyback


class GuiMainConf(TypedDict):
    auth: GuiAuth
    conn: GuiConn
    sections: dict[str, _SectionType]
    cache_age: int
    piggyback_host: str
    discovery: GuiDiscovery
    instances: list[GuiInstance]
    options: GuiOptions


class GuiAllConf(TypedDict):
    main: GuiMainConf
    other: list[GuiMainConf]


class SqlOptions(TypedDict):
    max_connections: NotRequired[int]
    ignore_inactive_local_instances: NotRequired[bool]


class SqlAuth(TypedDict):
    username: str
    password: NotRequired[str]
    type: Literal["sql_server", "integrated"]


class SqlTls(TypedDict):
    ca: str
    client_certificate: str


class SqlConn(TypedDict):
    hostname: str
    fail_over_partner: NotRequired[str]
    port: NotRequired[int]
    timeout: NotRequired[int]
    trust_server_certificate: NotRequired[bool]
    tls: NotRequired[SqlTls]
    backend: NotRequired[str]
    exclude_databases: NotRequired[list[str]]


class SqlSection(TypedDict):
    is_async: NotRequired[bool]
    disabled: NotRequired[bool]
    sep: NotRequired[str]


class SqlPiggyback(TypedDict):
    hostname: str
    sections: NotRequired[list[dict[str, SqlSection | None]]]
    cache_age: NotRequired[int]


class SqlInstance(TypedDict):
    sid: str
    authentication: NotRequired[SqlAuth]
    connection: NotRequired[SqlConn]
    alias: NotRequired[str]
    piggyback: NotRequired[SqlPiggyback]


class SqlDiscovery(TypedDict):
    detect: bool
    include: NotRequired[list[str]]
    exclude: NotRequired[list[str]]


class SqlMain(TypedDict):
    authentication: SqlAuth
    connection: NotRequired[SqlConn]
    sections: NotRequired[list[dict[str, SqlSection | None]]]
    cache_age: NotRequired[int]
    piggyback_host: NotRequired[str]
    discovery: NotRequired[SqlDiscovery]
    instances: NotRequired[list[SqlInstance]]
    options: NotRequired[SqlOptions]


class SqlMainEntry(TypedDict):
    main: SqlMain


class SqlOutput(TypedDict):
    main: SqlMain
    configs: NotRequired[list[SqlMainEntry]]


def check_get_ms_sql_files(conf: GuiAllConf) -> FileGenerator:
    for o_s in OS_Setups:
        main = conf.get("main")  # Start with a list containing the first element of the tuple
        if main and _is_allowed(main, o_s.base_os):  # type: ignore[redundant-expr]
            configs = [main]
            if (others := conf.get("other")) is not None:  # type: ignore[comparison-overlap]
                configs.extend(others)
            yield Plugin(
                base_os=o_s.base_os,
                target=o_s.plugin_target,
                source=o_s.plugin_source,
            )
            yield PluginConfig(
                base_os=o_s.base_os,
                lines=list(_get_mssql_yaml_lines(configs)),
                target=Path(o_s.config_name),
            )


def _get_mssql_yaml_lines(configs: Sequence[GuiMainConf]) -> Iterable[str]:
    result = {"mssql": _create_mssql_dict(configs)}
    yield "---"  # according to spec in Jira
    yield from yaml.dump(result, indent=2, sort_keys=False).splitlines()


def _create_mssql_dict(configs: Sequence[GuiMainConf]) -> SqlOutput:
    main = _create_main(configs[0])
    output = SqlOutput(main=main)
    if len(configs) > 1:
        output["configs"] = _to_configs(configs[1:])

    return output


def _create_main(conf: GuiMainConf) -> SqlMain:
    auth_type: GuiAuth = conf.get("auth", "local")
    main = SqlMain(authentication=_to_sql_auth(auth_type))
    if conn := conf.get("conn"):
        main["connection"] = _to_sql_conn(conn)

    if cache_age := conf.get("cache_age"):
        main["cache_age"] = cache_age
    if piggyback_host := conf.get("piggyback_host"):
        main["piggyback_host"] = piggyback_host
    if (sections := _to_sql_sections(conf.get("sections"))) is not None:
        main["sections"] = sections
    if discovery := conf.get("discovery"):
        main["discovery"] = _to_sql_discovery(discovery)

    if instances := conf.get("instances"):
        main["instances"] = _to_sql_instances(instances)
    if (options := _to_options(conf.get("options"))) is not None:
        main["options"] = options

    return main


def _to_sql_conn(conn: GuiConn) -> SqlConn:
    connection = SqlConn(hostname="localhost")
    if hostname := conn.get("hostname"):
        connection["hostname"] = hostname
    if fail_over_partner := conn.get("fail_over_partner"):
        connection["fail_over_partner"] = fail_over_partner
    if port := conn.get("port"):
        connection["port"] = port
    if timeout := conn.get("timeout"):
        connection["timeout"] = timeout
    if (trust := conn.get("trust_server_certificate")) is not None:  # type: ignore[comparison-overlap]
        connection["trust_server_certificate"] = trust
    if tls := _to_tls(conn.get("tls")):
        connection["tls"] = tls
    if backend := conn.get("backend"):
        connection["backend"] = backend
    if exclude_databases := conn.get("exclude_databases"):
        connection["exclude_databases"] = list(exclude_databases)
    return connection


def _to_sql_sections(
    sections: dict[str, _SectionType] | None,
) -> list[dict[str, SqlSection | None]] | None:
    return (
        [{name: _to_sql_section(kind=kind)} for name, kind in sections.items() if kind is not None]
        if sections
        else None
    )


def _to_sql_section(kind: _SectionType) -> SqlSection | None:
    if kind == "sync":
        return None
    section = SqlSection()
    match kind:
        case "async":
            section["is_async"] = True
        case "disabled":
            section["disabled"] = True

    return section


def _to_sql_discovery(discovery: GuiDiscovery) -> SqlDiscovery:
    d = SqlDiscovery(detect=discovery[0])
    combi_list = discovery[1]
    if isinstance(combi_list, tuple):
        match combi_list[0]:
            case "include":
                d["include"] = combi_list[1]
            case "exclude":
                d["exclude"] = combi_list[1]

    return d


def _to_sql_instances(instances: Iterable[GuiInstance]) -> list[SqlInstance]:
    return [_to_sql_instance(i) for i in instances]


def _to_sql_instance(instance: GuiInstance) -> SqlInstance:
    i = SqlInstance(sid=instance["sid"])
    if conn := instance.get("conn"):
        i["connection"] = _to_sql_conn(conn)
    if auth := instance.get("auth"):
        i["authentication"] = _to_sql_auth(auth)
    if alias := instance.get("alias"):
        i["alias"] = alias
    if piggyback := instance.get("piggyback"):
        i["piggyback"] = _to_sql_piggyback(piggyback)
    return i


def _to_configs(configs: Iterable[GuiMainConf]) -> list[SqlMainEntry]:
    return [SqlMainEntry(main=_create_main(i)) for i in configs]


def _to_sql_piggyback(piggyback: GuiPiggyback) -> SqlPiggyback:
    p = SqlPiggyback(hostname=piggyback["hostname"])
    if cache_age := piggyback.get("cache_age"):
        p["cache_age"] = cache_age
    if (sections := _to_sql_sections(piggyback.get("sections"))) is not None:
        p["sections"] = sections

    return p


def _to_sql_auth(auth_type: GuiAuth) -> SqlAuth:
    match auth_type:
        case "local":
            return SqlAuth(username="", type="integrated")
        case ("remote", (u, p)):
            return SqlAuth(username=str(u), password=password_store.extract(p), type="sql_server")
        case _:
            return SqlAuth(username="", type="integrated")


def _to_options(options: GuiOptions | None) -> SqlOptions | None:
    if options is None:
        return None

    sql_options = SqlOptions()
    if max_connections := options.get("max_connections"):
        sql_options["max_connections"] = max_connections
    if options.get("ignore_inactive_local_instances"):
        sql_options["ignore_inactive_local_instances"] = True

    return sql_options or None


def _to_tls(tls: GuiTls | None) -> SqlTls | None:
    if tls is None:
        return None

    if client_certificate := tls.get("client_certificate"):
        return SqlTls(ca="", client_certificate=client_certificate)

    return None


def _to_exclude_databases(gui_data: Sequence[str] | None) -> list[str]:
    if gui_data is None:
        return []
    return [value for flag, value in zip(gui_data, _SYSTEM_DATABASES) if flag]


def _is_allowed(conf: GuiMainConf, base_os: OS) -> bool:
    auth_type: GuiAuth = conf.get("auth", "local")
    return auth_type != "local" or base_os is OS.WINDOWS


register.bakery_plugin(
    name="mk_ms_sql",
    files_function=check_get_ms_sql_files,
)
