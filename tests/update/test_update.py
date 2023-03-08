#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.version import Edition

from .conftest import get_host_data, get_site_status, update_config, update_site, version_supported

logger = logging.getLogger(__name__)


@pytest.mark.type("update")
def test_update(test_site: Site) -> None:
    # TODO: check source installation (version check done in test_site fixture)
    # TODO: set config

    # get baseline monitoring data
    base_data = get_host_data(test_site)
    logger.debug("Base data: %s", base_data)

    # get version data
    base_version = test_site.version
    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    target_site = update_site(target_version)

    # TODO: check target installation (version check done in update_site function)
    # TODO: check config

    # Dumping cmc config as parseable object (JSON)
    # cmk --dump-cmc-config

    # Triggering cmk config update
    update_config_result = update_config(target_site)
    if version_supported(base_version.version):
        assert update_config_result == 0, "Updating the configuration failed unexpectedly!"
    else:
        assert (
            update_config_result != 0
        ), "Updating the configuration succeeded for an unsupported release!"
        assert (
            update_config_result != 2
        ), "Trying to update the config resulted in an unexpected error!"

    # get update monitoring data
    target_data = get_host_data(target_site)
    logger.debug("Target data: %s", target_data)

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    # TODO: Compare data
