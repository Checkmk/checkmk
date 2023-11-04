#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container

from cmk.utils.validatedstr import ValidatedString


class RuleSetName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return frozenset(("fileinfo-groups",))
