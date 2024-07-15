#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir


class ConfigBundle(TypedDict):
    """
    A configuration bundle is a collection of configs which are managed together by this bundle.
    Each underlying config must have the locked_by attribute set to the id of the bundle. We
    explicitly avoid double references here to keep the data model simple. The group and program
    combination should determine which configuration objects are potentially part of the bundle.
    """

    # General properties
    id: str
    title: str
    comment: str

    # Bundle specific properties
    group: str
    program_id: Literal["quick_setup"]
    customer: NotRequired[str]  # CME specific


class ConfigBundleStore(WatoSingleConfigFile[ConfigBundle]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(multisite_dir()) / "configuration_bundles.mk",
            config_variable="configuration_bundles",
            spec_class=ConfigBundle,
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(ConfigBundleStore())
