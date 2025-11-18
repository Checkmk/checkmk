#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui.openapi.framework.model import json_dump_without_omitted


def dump_dict_without_omitted[T](instance_type: type[T], instance: T) -> dict[str, object]:
    """Serialize the given API instance to a dict, removing omitted fields.

    Notes:
        * This function cares more about relying on the same conversion mechanism rather than
        being performant

    """
    json_bytes = json_dump_without_omitted(instance_type, instance, is_testing=False)
    return json.loads(json_bytes)  # type: ignore[no-any-return]
