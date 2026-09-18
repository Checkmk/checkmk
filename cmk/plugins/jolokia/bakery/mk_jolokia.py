#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence
from dataclasses import astuple, dataclass
from pathlib import Path
from pprint import pformat
from typing import Literal, Never, Self

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, FileGenerator, OS, Plugin, PluginConfig, Secret

type _ValueTypeType = Literal["number", "string", "rate"]


class LoginConfig(BaseModel, frozen=True):
    """Login configuration for Jolokia."""

    user: str = "monitoring"
    password: Secret
    mode: Literal["basic", "digest"] = "basic"


class SetupConfigCustomVars(BaseModel, frozen=True):
    mbean: str
    path: str
    value_type: _ValueTypeType
    title: str | None = None


type _VerifyConfig = (
    tuple[Literal["trust_store", "disabled"], None] | tuple[Literal["ca_file"], str]
)


class SetupConfigElement(BaseModel, frozen=True):
    protocol: Literal["http", "https"] | None = None
    verify: _VerifyConfig | None = None
    server: tuple[str, str | None] | None = None
    port: int | None = None
    timeout: float | None = None
    login: LoginConfig | None = None
    suburi: str | None = None
    instance: str | None = None
    custom_vars: Sequence[SetupConfigCustomVars] = ()


class SetupConfig(SetupConfigElement):
    instances: Sequence[SetupConfigElement] = ()
    deployment: Literal["sync", "do_not_deploy"] | None = None


type PluginConfigInstanceKey = Literal[
    "protocol",
    "verify",
    "server",
    "port",
    "timeout",
    "user",
    "password",
    "mode",
    "suburi",
    "instance",
    "custom_vars",
]


@dataclass(frozen=True)
class PluginConfigCustomVars:
    """represents the custom_var entry as expected by the mk_jolokia agent plugin"""

    mbean: str
    path: str
    title: str
    itemspec: list[Never]  # not configurable via Setup
    do_search: Literal[False]  # not configurable via Setup
    value_type: _ValueTypeType

    @classmethod
    def from_setup(
        cls,
        custom_var: SetupConfigCustomVars,
    ) -> Self:
        return cls(
            mbean=custom_var.mbean,
            path=custom_var.path,
            title=custom_var.path if custom_var.title is None else custom_var.title,
            itemspec=[],
            do_search=False,
            value_type=custom_var.value_type,
        )


def get_mk_jolokia_files(config: SetupConfig) -> FileGenerator:
    if config.deployment == "do_not_deploy":
        return

    for base_os in [OS.LINUX, OS.WINDOWS]:
        yield Plugin(base_os=base_os, source=Path("mk_jolokia.py"))

        yield PluginConfig(
            base_os=base_os,
            lines=list(_get_mk_jolokia_config(config)),
            target=Path("jolokia.cfg"),
            include_header=True,
        )


def _get_mk_jolokia_config(conf: SetupConfig) -> Iterable[str]:
    yield "# Default values"

    for key, value in _key_value_pairs(conf):
        yield from f"{key} = {pformat(value)}".split("\n")

    if conf.instances:
        yield ""
        yield "# Instances"
        instance_entries = [dict(_key_value_pairs(instance)) for instance in conf.instances]
        yield from f"instances = {pformat(instance_entries)}".split("\n")


def _key_value_pairs(
    options: SetupConfigElement,
) -> Iterable[tuple[PluginConfigInstanceKey, object]]:
    if options.protocol is not None:
        yield "protocol", options.protocol
    if options.verify is not None:
        yield "verify", _transform_verify_conf(options.verify)
    yield "server", _transform_server_conf(options.server)
    if options.port is not None:
        yield "port", options.port
    if options.timeout is not None:
        yield "timeout", options.timeout
    if options.login is not None:
        yield "user", options.login.user
        yield "password", options.login.password.revealed
        yield "mode", options.login.mode
    if options.suburi is not None:
        yield "suburi", options.suburi
    if options.instance is not None:
        yield "instance", options.instance
    if options.custom_vars:
        yield (
            "custom_vars",
            [
                astuple(PluginConfigCustomVars.from_setup(custom_var_dict))
                for custom_var_dict in options.custom_vars
            ],
        )


def _transform_verify_conf(value: _VerifyConfig) -> bool | str:
    """Map the verification choice onto the `verify` value expected by mk_jolokia."""
    match value:
        case ("ca_file", path):
            return path
        case ("disabled", _):
            return False
        case ("trust_store", _):
            return True


def _transform_server_conf(value: tuple[str, str | None] | None) -> str:
    """Transform server configuration from v1 CascadingSingleChoice format.

    The Setup rulespec uses a CascadingSingleChoice with two options:
    - ("ip_or_fqdn", "IP-ADDR"): Use the provided IP address or FQDN
    - ("use_local_fqdn", None): Use the FQDN of the monitored host

    The agent plugin expects:
    - An IP address or FQDN as a string (e.g., "127.0.0.1" or "server.example.com")
    - The special string "use fqdn" to indicate it should use the local FQDN
    """
    if value is None or value[0] == "use_local_fqdn":
        return "use fqdn"
    return value[1] or "use fqdn"


bakery_plugin_jolokia = BakeryPlugin(
    name="mk_jolokia",
    parameter_parser=SetupConfig.model_validate,
    default_parameters=None,
    files_function=get_mk_jolokia_files,
)
