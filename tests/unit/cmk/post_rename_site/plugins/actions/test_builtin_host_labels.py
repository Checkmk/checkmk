#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from pytest import MonkeyPatch

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.plugins.checkmk.post_rename_site.builtin_host_labels import (
    update_builtin_host_labels_site,
)
from cmk.ruleset_matcher.labels import BuiltinHostLabelsStore


def test_update_builtin_host_labels_site_refreshes_site_and_preserves_customer(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    labels_file = tmp_path / "builtin_host_labels.mk"
    monkeypatch.setattr(cmk.utils.paths, "builtin_host_labels_file", labels_file)
    BuiltinHostLabelsStore(labels_file).save({"cmk/site": "old_site", "cmk/customer": "customer1"})

    update_builtin_host_labels_site(SiteId("old_site"), SiteId("new_site"), logging.getLogger())

    # cmk/site is refreshed to the new site id; cmk/customer (unaffected by a rename) is kept.
    assert BuiltinHostLabelsStore(labels_file).load() == {
        "cmk/site": "new_site",
        "cmk/customer": "customer1",
    }
