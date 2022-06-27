#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Iterable


def unique_default_name_suggestion(template: str, used_names: Iterable[str]) -> str:
    used_names_set = set(used_names)
    nr = 1
    while True:
        suggestion = "%s_%d" % (template.replace(" ", "_"), nr)
        if suggestion not in used_names_set:
            return suggestion
        nr += 1
