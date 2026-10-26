#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal, NamedTuple, NotRequired, TypedDict

import yaml
from pydantic import BaseModel

from cmk.utils.password_store import extract_formspec_password, FormSpecPassword

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


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


class _Credentials(BaseModel):
    user: str
    password: FormSpecPassword


_Auth = tuple[Literal["local"], None] | tuple[Literal["remote"], _Credentials]

_SectionMode = Literal["sync", "asynchronous", "disabled"]


class _Tls(BaseModel):
    client_certificate: str = ""


class _Conn(BaseModel):
    hostname: str = ""
    fail_over_partner: str = ""
    port: int | None = None
    timeout: int | None = None
    trust_server_certificate: bool | None = None
    tls: _Tls | None = None
    backend: str = ""
    exclude_databases: Sequence[str] = ()


class _Discovery(BaseModel):
    detect: bool
    instances: tuple[Literal["all"], None] | tuple[Literal["include", "exclude"], Sequence[str]]


class _Options(BaseModel):
    max_connections: int | None = None
    ignore_inactive_local_instances: bool = False


class _Piggyback(BaseModel):
    hostname: str = ""
    sections: Mapping[str, _SectionMode] | None = None
    cache_age: int | None = None


class _Instance(BaseModel):
    sid: str
    auth: _Auth | None = None
    conn: _Conn | None = None
    alias: str = ""
    piggyback: _Piggyback | None = None


class _MainConf(BaseModel):
    auth: _Auth = ("local", None)
    conn: _Conn | None = None
    sections: Mapping[str, _SectionMode] | None = None
    cache_age: int | None = None
    piggyback_host: str = ""
    discovery: _Discovery | None = None
    instances: Sequence[_Instance] = ()
    options: _Options | None = None


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync"], None]
    main: _MainConf = _MainConf()
    other: Sequence[_MainConf] = ()


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


def check_get_ms_sql_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return
    for o_s in OS_Setups:
        if _is_allowed(config.main, o_s.base_os):
            yield Plugin(
                base_os=o_s.base_os,
                target=o_s.plugin_target,
                source=o_s.plugin_source,
            )
            yield PluginConfig(
                base_os=o_s.base_os,
                lines=list(_get_mssql_yaml_lines([config.main, *config.other])),
                target=Path(o_s.config_name),
            )


def _get_mssql_yaml_lines(configs: Sequence[_MainConf]) -> Iterable[str]:
    result = {"mssql": _create_mssql_dict(configs)}
    yield "---"  # according to spec in Jira
    yield from yaml.dump(result, indent=2, sort_keys=False).splitlines()


def _create_mssql_dict(configs: Sequence[_MainConf]) -> SqlOutput:
    main = _create_main(configs[0])
    output = SqlOutput(main=main)
    if len(configs) > 1:
        output["configs"] = _to_configs(configs[1:])

    return output


def _create_main(conf: _MainConf) -> SqlMain:
    main = SqlMain(authentication=_to_sql_auth(conf.auth))
    if conf.conn is not None and conf.conn.model_fields_set:
        main["connection"] = _to_sql_conn(conf.conn)

    if conf.cache_age:
        main["cache_age"] = conf.cache_age
    if conf.piggyback_host:
        main["piggyback_host"] = conf.piggyback_host
    if (sections := _to_sql_sections(conf.sections)) is not None:
        main["sections"] = sections
    if conf.discovery is not None:
        main["discovery"] = _to_sql_discovery(conf.discovery)

    if conf.instances:
        main["instances"] = _to_sql_instances(conf.instances)
    if (options := _to_options(conf.options)) is not None:
        main["options"] = options

    return main


def _to_sql_conn(conn: _Conn) -> SqlConn:
    connection = SqlConn(hostname=conn.hostname or "localhost")
    if conn.fail_over_partner:
        connection["fail_over_partner"] = conn.fail_over_partner
    if conn.port:
        connection["port"] = conn.port
    if conn.timeout:
        connection["timeout"] = conn.timeout
    if conn.trust_server_certificate is not None:
        connection["trust_server_certificate"] = conn.trust_server_certificate
    if tls := _to_tls(conn.tls):
        connection["tls"] = tls
    if conn.backend:
        connection["backend"] = conn.backend
    if conn.exclude_databases:
        connection["exclude_databases"] = list(conn.exclude_databases)
    return connection


def _to_sql_sections(
    sections: Mapping[str, _SectionMode] | None,
) -> list[dict[str, SqlSection | None]] | None:
    # mk-sql runs only the listed sections, so a disabled section is left out.
    return (
        [{name: _to_sql_section(mode)} for name, mode in sections.items() if mode != "disabled"]
        if sections
        else None
    )


def _to_sql_section(mode: Literal["sync", "asynchronous"]) -> SqlSection | None:
    return None if mode == "sync" else SqlSection(is_async=True)


def _to_sql_discovery(discovery: _Discovery) -> SqlDiscovery:
    d = SqlDiscovery(detect=discovery.detect)
    match discovery.instances:
        case ("include", instances):
            d["include"] = list(instances)
        case ("exclude", instances):
            d["exclude"] = list(instances)
        case ("all", _):
            pass

    return d


def _to_sql_instances(instances: Iterable[_Instance]) -> list[SqlInstance]:
    return [_to_sql_instance(i) for i in instances]


def _to_sql_instance(instance: _Instance) -> SqlInstance:
    i = SqlInstance(sid=instance.sid)
    if instance.conn is not None and instance.conn.model_fields_set:
        i["connection"] = _to_sql_conn(instance.conn)
    if instance.auth is not None:
        i["authentication"] = _to_sql_auth(instance.auth)
    if instance.alias:
        i["alias"] = instance.alias
    # The old rule set allowed to tick the piggyback option without a host name.
    if instance.piggyback is not None and instance.piggyback.hostname:
        i["piggyback"] = _to_sql_piggyback(instance.piggyback)
    return i


def _to_configs(configs: Iterable[_MainConf]) -> list[SqlMainEntry]:
    return [SqlMainEntry(main=_create_main(i)) for i in configs]


def _to_sql_piggyback(piggyback: _Piggyback) -> SqlPiggyback:
    p = SqlPiggyback(hostname=piggyback.hostname)
    if piggyback.cache_age:
        p["cache_age"] = piggyback.cache_age
    if (sections := _to_sql_sections(piggyback.sections)) is not None:
        p["sections"] = sections

    return p


def _to_sql_auth(auth: _Auth) -> SqlAuth:
    match auth:
        case ("local", _):
            return SqlAuth(username="", type="integrated")
        case ("remote", credentials):
            return SqlAuth(
                username=credentials.user,
                password=extract_formspec_password(credentials.password),
                type="sql_server",
            )


def _to_options(options: _Options | None) -> SqlOptions | None:
    if options is None:
        return None

    sql_options = SqlOptions()
    if options.max_connections:
        sql_options["max_connections"] = options.max_connections
    if options.ignore_inactive_local_instances:
        sql_options["ignore_inactive_local_instances"] = True

    return sql_options or None


def _to_tls(tls: _Tls | None) -> SqlTls | None:
    if tls is None or not tls.client_certificate:
        return None
    return SqlTls(ca="", client_certificate=tls.client_certificate)


def _is_allowed(conf: _MainConf, base_os: OS) -> bool:
    return conf.auth[0] != "local" or base_os is OS.WINDOWS


register.bakery_plugin(
    name="mk_ms_sql",
    files_function=check_get_ms_sql_files,
)
