#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
from typing import Iterator

from cmk.utils.type_defs import UserId

from cmk.gui import visuals
from cmk.gui.type_defs import VisualTypeName


def update_visuals(
    visual_type: VisualTypeName,
    all_visuals: dict[tuple[UserId, str], visuals.T],
) -> None:
    with _save_user_visuals(visual_type, all_visuals) as affected_user:
        # skip builtins, only users
        affected_user.update(owner for owner, _name in all_visuals if owner)


@contextmanager
def _save_user_visuals(
    visual_type: VisualTypeName,
    all_visuals: dict[tuple[UserId, str], visuals.T],
) -> Iterator[set[UserId]]:
    modified_user_instances: set[UserId] = set()

    yield modified_user_instances

    # Now persist all modified instances
    for user_id in modified_user_instances:
        visuals.save(visual_type, all_visuals, user_id)
