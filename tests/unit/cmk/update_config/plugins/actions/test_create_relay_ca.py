#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.create_relay_ca import CreateRelayCA
from cmk.utils.certs import cert_dir, RelaysCA

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def update_action() -> CreateRelayCA:
    return CreateRelayCA(
        name="create-relay-ca",
        title="Create relay CA",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_300,
        continue_on_failure=True,
    )


def test_create_relay_ca_creates_when_missing(tmp_path: Path, update_action: CreateRelayCA) -> None:
    ca_path = cert_dir(tmp_path)
    ca_file = RelaysCA._ca_file(ca_path)
    assert not ca_file.exists()

    update_action(LOGGER, site_root=tmp_path, site_id=SiteId("testsite"))

    _ = RelaysCA.load(ca_path)


def test_create_relay_ca_idempotent(tmp_path: Path, update_action: CreateRelayCA) -> None:
    ca_path = cert_dir(tmp_path)

    update_action(LOGGER, site_root=tmp_path, site_id=SiteId("testsite"))
    ca_file = RelaysCA._ca_file(ca_path)
    first_content = ca_file.read_bytes()

    update_action(LOGGER, site_root=tmp_path, site_id=SiteId("testsite"))
    second_content = ca_file.read_bytes()

    assert first_content == second_content
