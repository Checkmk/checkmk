# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2_unstable import BakeryPlugin, FileGenerator, OS, Plugin

HyperVPluginName = Literal["hyperv_host"]

_PLUGIN_MAPPING = {
    "hyperv_host": "hyperv_host.ps1",
}


class Config(BaseModel):
    deploy: (
        tuple[Literal["deploy"], Sequence[HyperVPluginName]] | tuple[Literal["do_not_deploy"], None]
    )


def get_hyperv_multiple_files(conf: Config) -> FileGenerator:
    choice, plugins = conf.deploy
    if choice == "deploy" and plugins:
        yield from (
            Plugin(base_os=OS.WINDOWS, source=Path(_PLUGIN_MAPPING[plugin_name]))
            for plugin_name in plugins
        )


bakery_plugin_hyperv_collection = BakeryPlugin(
    name="hyperv_collection",
    parameter_parser=Config.model_validate,
    default_parameters=None,
    files_function=get_hyperv_multiple_files,
)
