#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import override

from cmk.ccc import store
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.gui.watolib.tags import load_tag_config_read_only, TagConfigFile
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir
from cmk.utils.tags import (
    AuxTag,
    AuxTagList,
    GroupedTag,
    TagConfig,
    TagConfigSpec,
    TagGroup,
    TagGroupID,
    TagID,
)


class AnonymizedTagConfigFile(TagConfigFile):
    def __init__(self, anon_interface: AnonInterface) -> None:
        super().__init__()
        self._config_file_path = anon_interface.relative_to_anon_dir(multisite_dir() / "tags.mk")
        self._anon_interface = anon_interface

    @override
    def save(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        self._save_gui_config(cfg, pprint_value)
        self._save_base_config(cfg, pprint_value)

    @override
    def _save_base_config(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        anon_base_config_path = self._anon_interface.relative_to_anon_dir(
            wato_root_dir() / "tags.mk"
        )
        anon_base_config_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            anon_base_config_path, key="tag_config", value=cfg, pprint_value=pprint_value
        )


class HostTagsStep(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        logger.warning("Process host tags")

        # Only custom tags
        tag_config = load_tag_config_read_only()

        anon_aux_tags = AuxTagList([])
        for aux_tag in tag_config.aux_tag_list.get_tags():
            anon_id = anon_interface.get_id_of_aux_tag(aux_tag.id)
            anon_aux_tag = AuxTag(
                tag_id=TagID(anon_id),
                title=f"Title of {anon_id}",
                help=f"Help of {anon_id}",
                topic=anon_interface.get_tag_topic(aux_tag.topic) if aux_tag.topic else None,
            )
            anon_aux_tags.append(anon_aux_tag)

        anon_tag_groups = []
        for tag_group in tag_config.tag_groups:
            anon_tag_group_id = anon_interface.get_id_of_tag_group(tag_group.id)
            anon_tags = []

            anon_group_topic = (
                anon_interface.get_tag_topic(tag_group.topic) if tag_group.topic else None
            )

            anon_group = TagGroup(
                group_id=TagGroupID(anon_tag_group_id),
                title=f"Title of {anon_tag_group_id}",
                help=f"Help of {anon_tag_group_id}",
                topic=anon_group_topic,
                tags=[],
            )
            for tag in tag_group.tags:
                anon_t_id = anon_interface.get_id_of_tag(tag.id) if tag.id else None
                anon_tags.append(
                    GroupedTag(
                        tag_id=TagID(anon_t_id) if anon_t_id else None,
                        title=f"Title of {anon_t_id}",
                        group=anon_group,
                        aux_tag_ids=[
                            TagID(anon_interface.get_id_of_aux_tag(aux_tag_id))
                            for aux_tag_id in tag.aux_tag_ids
                        ],
                    )
                )

            anon_tag_group = TagGroup(
                group_id=TagGroupID(anon_tag_group_id),
                title=f"Title of {anon_tag_group_id}",
                help=f"Help of {anon_tag_group_id}",
                topic=anon_group_topic,
                tags=anon_tags,
            )
            anon_tag_groups.append(anon_tag_group)

        anon_tag_config_spec = TagConfig(
            tag_groups=anon_tag_groups, aux_tags=anon_aux_tags
        ).get_dict_format()
        anon_config_file = AnonymizedTagConfigFile(anon_interface)
        anon_config_file.save(anon_tag_config_spec, pprint_value=True)


anonymize_step_host_tags = HostTagsStep()
