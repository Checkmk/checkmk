#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from pprint import pformat
from typing import Literal

from pydantic import BaseModel

from cmk.utils.password_store import extract_formspec_password

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class Instance(BaseModel):
    ashost: str
    sysnr: str
    client: str
    user: str
    passwd: (
        tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
        | tuple[Literal["cmk_postprocessed"], Literal["explicit_password"], tuple[str, str]]
    )
    trace: str
    lang: str
    host_prefix: str | None = None


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    instances: Sequence[Instance] = ()
    paths: Sequence[str] = (
        "SAP BI Monitors/BI Monitor",
        "SAP BI Monitors/BI Monitor/*/Oracle/Performance",
        "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*",
        "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/CPU_Utilization",
    )


def get_mk_sap_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    interval = None if (v := config.deployment[1]) is None else int(v)
    yield Plugin(base_os=OS.LINUX, source=Path("mk_sap.py"), interval=interval)
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_sap_config(config)),
        target=Path("sap.cfg"),
        include_header=True,
    )


def _get_mk_sap_config(config: _Config) -> Iterator[str]:
    yield "# Instances to monitor"
    cfgs = []
    for instance in config.instances:
        c: dict[str, object] = {
            "ashost": instance.ashost,
            "client": instance.client,
            "lang": instance.lang,
            "loglevel": "warn",
            "passwd": extract_formspec_password(instance.passwd),
            "sysnr": instance.sysnr,
            "trace": instance.trace,
            "user": instance.user,
        }
        if instance.host_prefix is not None:
            c["host_prefix"] = instance.host_prefix
        cfgs.append(c)
    yield from f"cfg = {pformat(cfgs)}".split("\n")
    yield ""
    yield ""
    yield "# CCMS paths to monitor"
    yield from f"monitor_paths += {pformat(list(config.paths), width=120)}".split("\n")


register.bakery_plugin(
    name="mk_sap",
    files_function=get_mk_sap_files,
)
