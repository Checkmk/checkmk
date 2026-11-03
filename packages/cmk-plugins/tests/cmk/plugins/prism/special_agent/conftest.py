# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
import responses


@pytest.fixture(name="api")
def _api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as api:
        yield api
