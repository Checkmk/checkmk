# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.agent_based.v2 import StringTable

V4_FIXTURES = Path(__file__).parent.parent / "special_agent" / "v4_fixtures"


@pytest.fixture(name="v4_cluster_section")
def _v4_cluster_section() -> Callable[[str], StringTable]:
    """What the v4 agent writes for a cluster of a Prism Central 7.5 lab, by cluster name"""

    def load(name: str) -> StringTable:
        return [[(V4_FIXTURES / f"section_prism_info_v2_{name}.json").read_text()]]

    return load
