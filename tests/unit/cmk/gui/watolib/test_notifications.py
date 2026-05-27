#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from typing import cast

import pytest

from tests.unit.cmk.web_test_app import SetConfig

from cmk.ccc import store

from cmk.utils.notify_types import (
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterSpecs,
    NotifyPluginParamsDict,
)

from cmk.gui.watolib.notifications import NotificationParameterConfigFile


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("pprint_value", [True, False])
def test_notification_parameter_config_file_preserves_parameter_order(
    tmp_path: Path,
    set_config: SetConfig,
    pprint_value: bool,
) -> None:
    # IDs whose alphabetically sorted order differs from the insertion order below.
    ids = [NotificationParameterID(i) for i in ("f9", "a1", "c3", "02", "7d")]
    parameters: NotificationParameterSpecs = {
        "mail": {
            id_: NotificationParameterItem(
                general=NotificationParameterGeneralInfos(
                    description=f"param-{nr}", comment="", docu_url=""
                ),
                parameter_properties=cast(NotifyPluginParamsDict, {}),
            )
            for nr, id_ in enumerate(ids)
        }
    }

    target_path = tmp_path / "notification_parameter.mk"
    with set_config(wato_pprint_config=pprint_value):
        NotificationParameterConfigFile()._save_to_path(target_path, parameters)

    loaded: NotificationParameterSpecs = store.load_from_mk_file(
        target_path, key="notification_parameter", default={}, lock=False
    )
    assert list(loaded["mail"].keys()) == ids
