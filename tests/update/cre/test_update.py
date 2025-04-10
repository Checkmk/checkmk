#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_services_with_status

from tests.update.helpers import (
    bulk_discover_and_schedule,
    check_agent_receiver_error_log,
    check_services,
    get_target_version,
    update_site,
)

from cmk.ccc.version import Edition

logger = logging.getLogger(__name__)


@pytest.mark.cre
def test_update(test_setup: tuple[Site, Edition, bool, str]) -> None:
    base_site, target_edition, interactive_mode, hostname = test_setup

    # get baseline monitoring data for each host
    base_data = base_site.get_host_services(hostname)
    assert len(get_services_with_status(base_data, 0)) > 0

    target_site = update_site(base_site, get_target_version(target_edition), interactive_mode)

    bulk_discover_and_schedule(target_site, hostname)

    check_services(target_site, hostname, base_data)

    check_agent_receiver_error_log(target_site)
