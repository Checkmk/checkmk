#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register

PodmanSocketDetectionMethod = (
    tuple[Literal["auto"], None]
    | tuple[Literal["only_root_socket"], None]
    | tuple[Literal["only_user_sockets"], None]
    | tuple[Literal["manual"], Sequence[str]]
)

PodmanPiggybackNameMethod = Literal["name", "nodename_name", "name_id"]

PodmanConnectionMethod = (
    tuple[Literal["api"], PodmanSocketDetectionMethod] | tuple[Literal["cli"], None]
)


class PodmanConfig(BaseModel, frozen=True):
    deploy: bool
    connection_method: PodmanConnectionMethod = ("api", ("auto", None))
    piggyback_name_method: PodmanPiggybackNameMethod = "nodename_name"
    keep_non_zero_exit_containers: bool = True


def get_mk_podman_files(
    conf: Mapping[str, object],
) -> FileGenerator:
    confm = PodmanConfig.model_validate(conf)
    if not confm.deploy:
        return

    yield Plugin(base_os=OS.LINUX, source=Path("mk_podman.py"))

    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(_get_mk_podman_config(confm)),
        target=Path("mk_podman.cfg"),
        include_header=True,
    )


def _get_mk_podman_config(conf: PodmanConfig) -> Iterable[str]:
    yield "[PODMAN]"

    method, method_params = conf.connection_method
    yield f"connection_method: {method}"

    if method == "api" and method_params is not None:
        socket_method, socket_list = method_params
        yield f"socket_detection_method: {socket_method}"

        if socket_method == "manual" and socket_list:
            yield f"socket_paths: {','.join(socket_list)}"

    yield f"piggyback_name_method: {conf.piggyback_name_method}"
    yield f"keep_non_zero_exit_containers: {'true' if conf.keep_non_zero_exit_containers else 'false'}"


register.bakery_plugin(
    name="mk_podman",
    files_function=get_mk_podman_files,
)
