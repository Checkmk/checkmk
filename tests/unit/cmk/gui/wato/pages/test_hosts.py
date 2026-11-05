#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.http import request
from cmk.gui.wato.pages.hosts import ModeCreateCluster
from cmk.gui.watolib.hosts_and_folders import FolderTree


@pytest.mark.usefixtures("request_context")
def test_new_cluster_with_an_invalid_name_starts_without_a_name(tree: FolderTree) -> None:
    request.set_var("host", "host name")

    assert ModeCreateCluster._init_new_host_object(tree).name() == ""  # noqa: SLF001
