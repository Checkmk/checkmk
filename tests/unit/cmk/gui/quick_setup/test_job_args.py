#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import get_default_config
from cmk.gui.quick_setup.handlers.setup import QuickSetupActionJobArgs
from cmk.gui.quick_setup.handlers.stage import QuickSetupStageActionJobArgs
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode
from cmk.gui.quick_setup.v0_unstable.type_defs import ActionId, QuickSetupId, StageIndex
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.tags import get_effective_tag_config, TagConfig

_USER_PERMISSION_CONFIG = UserPermissionSerializableConfig(
    roles={}, user_roles={}, default_user_profile_roles=[]
)
_HOST_ATTRS = [
    CustomHostAttrSpec(
        type="TextAscii",
        name="location",
        title="Location",
        topic="basic",
        help="",
        show_in_table=True,
        add_custom_macro=False,
    )
]


def test_stage_action_job_args_keep_the_folder_tree_config() -> None:
    tags = get_effective_tag_config(get_default_config()["wato_tags"])
    args = QuickSetupStageActionJobArgs(
        job_uuid="uuid",
        quick_setup_id=QuickSetupId("setup"),
        action_id=ActionId("action"),
        stage_index=StageIndex(0),
        user_input_stages=[],
        language="en",
        user_permission_config=_USER_PERMISSION_CONFIG,
        site_configs=SiteConfigurations({}),
        debug=False,
        use_git=False,
        pprint_value=False,
        wato_hide_folders_without_read_permissions=True,
        wato_host_attrs=_HOST_ATTRS,
        tags=tags.get_dict_format(),
    )

    restored = QuickSetupStageActionJobArgs.model_validate_json(args.model_dump_json())

    assert restored.wato_hide_folders_without_read_permissions is True
    assert list(restored.wato_host_attrs) == _HOST_ATTRS
    assert TagConfig.from_config(restored.tags).get_dict_format() == tags.get_dict_format()


def test_action_job_args_keep_the_folder_tree_config() -> None:
    tags = get_effective_tag_config(get_default_config()["wato_tags"])
    args = QuickSetupActionJobArgs(
        quick_setup_id=QuickSetupId("setup"),
        action_id=ActionId("action"),
        user_input_stages=[],
        mode=QuickSetupActionMode.SAVE,
        object_id=None,
        user_permission_config=_USER_PERMISSION_CONFIG,
        site_configs=SiteConfigurations({}),
        debug=False,
        use_git=False,
        pprint_value=False,
        wato_hide_folders_without_read_permissions=True,
        wato_host_attrs=_HOST_ATTRS,
        tags=tags.get_dict_format(),
    )

    restored = QuickSetupActionJobArgs.model_validate_json(args.model_dump_json())

    assert restored.wato_hide_folders_without_read_permissions is True
    assert list(restored.wato_host_attrs) == _HOST_ATTRS
    assert TagConfig.from_config(restored.tags).get_dict_format() == tags.get_dict_format()
