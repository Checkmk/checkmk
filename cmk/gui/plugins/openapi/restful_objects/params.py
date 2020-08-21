#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Rename this to parameters, rename the other to 'global_params' or 'param_definitions'

import re
from typing import List

PARAM_RE = re.compile(r"{([a-z][a-z0-9_]*)}")


def path_parameters(path: str) -> List[str]:
    """Give all variables from a path-template.

    Examples:

        >>> path_parameters("/objects/{domain_type}/{primary_key}")
        ['domain_type', 'primary_key']

    Args:
        path:
            The path-template.

    Returns:
        A list of variable-names.

    """
    return PARAM_RE.findall(path)
