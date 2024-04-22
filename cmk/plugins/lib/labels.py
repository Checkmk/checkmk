#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping


def custom_tags_to_valid_labels(tags: Mapping[str, str]) -> Mapping[str, str]:
    # Make sure we only generate valid labels, i.e.
    # 1) no empty values - we insert "true" for now, but empty values will be allowed in the future
    #    see CMK-10380
    # 2) no colons allowed in either key or value
    labels: dict[str, str] = {}
    for key, value in tags.items():
        key = key.replace(":", "_")
        # TODO: allow empty values once CMK-10380 is done
        value = value.replace(":", "_") if value else "true"
        labels[key] = value
    return labels
