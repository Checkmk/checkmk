#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from contextlib import contextmanager

from cmk.utils.type_defs import UserId

from cmk.gui import visuals
from cmk.gui.query_filters import AllLabelGroupsQuery
from cmk.gui.type_defs import VisualTypeName
from cmk.gui.utils.labels import LabelGroups as _LabelGroups
from cmk.gui.valuespec import LabelGroups


def update_visuals(
    visual_type: VisualTypeName,
    all_visuals: dict[tuple[UserId, str], visuals.T],
) -> None:
    with _save_user_visuals(visual_type, all_visuals) as affected_user:
        # skip builtins, only users
        affected_user.update(owner for owner, _name in all_visuals if owner)
        _migrate_label_filter_configs(all_visuals)
        _set_packaged_key(all_visuals)


@contextmanager
def _save_user_visuals(
    visual_type: VisualTypeName,
    all_visuals: dict[tuple[UserId, str], visuals.T],
) -> Iterator[set[UserId]]:
    modified_user_instances: set[UserId] = set()
    try:
        yield modified_user_instances
    finally:
        # Now persist all modified instances
        for user_id in modified_user_instances:
            visuals.save(visual_type, all_visuals, user_id)


def _set_packaged_key(all_visuals: dict[tuple[UserId, str], visuals.T]) -> None:
    """2.2 introduced the mandatory key 'packaged', update old visuals with
    this key"""
    for (owner, _name), config in all_visuals.items():
        if not owner:
            continue
        if "packaged" in config:
            continue
        config["packaged"] = False


def _migrate_label_filter_configs(all_visuals: dict[tuple[UserId, str], visuals.T]) -> None:
    """
    Migrate host and service label filter configs in custom visual contexts
    Exemplary old visual context for a host label filter:
      {"host_labels": {
          "host_label": "[{'value':'a:b'},{'value':'c:d'}]",
      }}
    Exemplary new visual context for a host label filter:
      {"host_labels": {
          "host_labels_count": 1,
          "host_labels_1_bool": "and",
          "host_labels_1_vs_1_bool": "and",
          "host_labels_1_vs_1_vs": "a:b",
          "host_labels_1_vs_2_bool": "and",
          "host_labels_1_vs_2_vs": "c:d",
      }}
    """
    for (owner, _name), config in all_visuals.items():
        if not owner:
            continue

        for object_type in ["host", "service"]:
            ident = f"{object_type}_labels"
            ctx = config.get("context", {})
            labels_config = ctx.get(ident, {}).get(  # type: ignore[attr-defined]
                f"{object_type}_label"
            )

            if not labels_config:
                continue

            labels = [d.get("value") for d in json.loads(labels_config)]

            label_groups_dict = {
                f"{ident}_count": "1",
                f"{ident}_1_bool": "and",
                f"{ident}_1_vs_count": str(len(labels)),
            }

            for i, label in enumerate(labels, 1):
                label_id = f"{ident}_1_vs_{i}"
                label_groups_dict.update(
                    {
                        f"{label_id}_bool": "and",
                        f"{label_id}_vs": label,
                    }
                )

            # Build and validate the label groups value based on the above dict
            label_groups_value: _LabelGroups = AllLabelGroupsQuery(
                object_type=object_type  # type: ignore[arg-type]
            ).parse_value(label_groups_dict)
            LabelGroups().validate_value(value=label_groups_value, varprefix=ident)

            ctx[ident] = label_groups_dict  # type: ignore[index]
