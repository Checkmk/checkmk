#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]
    mtr_config: list[dict[str, Any]]


def get_mtr_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("mtr.py"),
        interval=None if (v := config.deployment[1]) is None else int(v),
    )
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mtr_config(config.mtr_config)),
        target=Path("mtr.cfg"),
        include_header=True,
    )


def _get_mtr_config(mtr_settings: Iterable[Mapping[str, Any]]) -> Iterable[str]:
    yield from [
        "# [DEFAULTS]",
        "# type=icmp    # icmp, tcp or udp",
        "# count=10     # number of pings per mtr report",
        "# force_ipv4=0 # force ipv4, exclusive with force_ipv6",
        "# force_ipv6=0 # force ipv6, exclusive with force_ipv4",
        "# size=64      # packet size",
        "# time=0       # minimum time between runs, 0 / default means run if mtr doesn't run anymore",
        "# port=80      # UDP/TCP port to connect to",
        "# dns=0        # Use DNS resolution to lookup addresses",
        "# address=     # Bind to source address",
        "# interval=    # time MTR waits between sending pings",
        "# timeout=     # ping Timeout, see mtr man page",
        "# max_hops=30  # maximum number of hops",
        "",
        "",
    ]

    for address_conf in mtr_settings:
        yield "[%s]" % address_conf["hostname"]
        for what in [
            "type",
            "count",
            "size",
            "time",
            "port",
            "address",
            "interval",
            "timeout",
            "max_hops",
        ]:
            if what in address_conf:
                yield f"{what} = {address_conf[what]}"

        if address_conf.get("dns"):
            yield "dns = %s" % (address_conf["dns"])

        if "enforce_what" in address_conf:
            yield "force_%s = True" % (address_conf["enforce_what"])

        yield ""


register.bakery_plugin(
    name="mtr",
    files_function=get_mtr_files,
)
