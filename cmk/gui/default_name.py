#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Iterable


def unique_default_name_suggestion(template: str, used_names: Iterable[str]) -> str:
    used_names_set = set(used_names)
    nr = 1
    while True:
        suggestion = "%s_%d" % (template.replace(" ", "_"), nr)
        if suggestion not in used_names_set:
            return suggestion
        nr += 1


def unique_clone_increment_suggestion(to_clone: str, used_names: Iterable[str]) -> str:
    template = re.sub("_[0-9]{1,}$", "", to_clone)

    return unique_default_name_suggestion(template=template, used_names=used_names)
