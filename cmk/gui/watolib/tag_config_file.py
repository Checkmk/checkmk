#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc import store
from cmk.gui import hooks
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir
from cmk.utils.tags import BuiltinTagConfig, TagConfig, TagConfigSpec


class TagConfigFile(WatoSingleConfigFile[TagConfigSpec]):
    """Handles loading the tag definitions from GUI tags.mk

    When saving the configuration it also writes out the tags.mk for the cmk.base world.
    """

    def __init__(self) -> None:
        super().__init__(
            config_file_path=multisite_dir() / "tags.mk",
            config_variable="wato_tags",
            spec_class=TagConfigSpec,
        )

    @override
    def _load_file(self, *, lock: bool) -> TagConfigSpec:
        default: TagConfigSpec = {"tag_groups": [], "aux_tags": []}
        return store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default=default,
            lock=lock,
        )

    @override
    def save(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        self._save_gui_config(cfg, pprint_value)
        self._save_base_config(cfg, pprint_value)
        hooks.call("tags-saved", cfg)

    def _save_gui_config(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        super().save(cfg, pprint_value)

    def _save_base_config(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            wato_root_dir() / "tags.mk", key="tag_config", value=cfg, pprint_value=pprint_value
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(TagConfigFile())


def load_tag_config_read_only() -> TagConfig:
    return TagConfig.from_config(TagConfigFile().load_for_reading())


def load_all_tag_config_read_only() -> TagConfig:
    """Load the tag config + the built in tag config.  Read Only"""
    tag_config = load_tag_config_read_only()
    tag_config += BuiltinTagConfig()
    return tag_config
