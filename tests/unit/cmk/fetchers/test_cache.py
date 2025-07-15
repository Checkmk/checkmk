#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging

from cmk.fetchers import Mode
from cmk.fetchers.filecache import MaxAge

from cmk.checkengine.parser import SectionStore


class TestSectionStore:
    def test_repr(self) -> None:
        assert isinstance(
            repr(
                SectionStore(
                    "/dev/null",
                    logger=logging.getLogger("test"),
                )
            ),
            str,
        )


class TestMaxAge:
    def test_repr(self) -> None:
        max_age = MaxAge(checking=42, discovery=69, inventory=1337)
        assert isinstance(repr(max_age), str)

    def test_serialize(self) -> None:
        max_age = MaxAge(checking=42, discovery=69, inventory=1337)
        assert MaxAge(*json.loads(json.dumps(max_age))) == max_age

    def test_get(self) -> None:
        max_age = MaxAge(checking=42, discovery=69, inventory=1337)
        assert max_age.get(Mode.CHECKING) == 42
        assert max_age.get(Mode.DISCOVERY) == 69
        assert max_age.get(Mode.INVENTORY) == 1337
        assert max_age.get(Mode.NONE) == 0
