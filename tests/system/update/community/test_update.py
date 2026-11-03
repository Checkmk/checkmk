#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from datetime import datetime, UTC

import pytest

from cmk.licensing.handler import LicenseState
from tests.system.update.helpers import (
    bulk_discover_and_schedule,
    check_errors_in_log_files,
    check_generated_files_present,
    check_services,
    check_unseeded_config_warning,
    get_target_package,
    plant_legacy_conf_d_file,
    update_site,
)
from tests.testlib.common.utils2 import get_services_with_status
from tests.testlib.common.version import TypeCMKEdition
from tests.testlib.system.site import Site

logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    os.getenv("DISTRO") == "almalinux-8", reason="Fails on almalinux-8 due to dependency issue."
)
@pytest.mark.skip_if_not_edition("community")
def test_update(test_setup: tuple[Site, TypeCMKEdition, bool, str]) -> None:
    base_site, target_edition, interactive_mode, hostname = test_setup

    assert base_site.edition.short == TypeCMKEdition.COMMUNITY.short

    # get baseline monitoring data for each host
    base_data = base_site.get_host_services(hostname)
    assert len(get_services_with_status(base_data, 0)) > 0

    check_generated_files_present(base_site)
    planted = plant_legacy_conf_d_file(base_site)

    if target_edition.is_community_edition():
        target_site = update_site(base_site, get_target_package(target_edition), interactive_mode)
    else:
        # An upgrade to Pro or Ultimate leaves the site waiting for the trial mode
        # selection, with a trial period starting at the upgrade. Checked here because
        # the cross edition jobs run this test; a test of its own would install another
        # base site. The helpers are non-free, so they are imported only for a non-free
        # target edition.
        from tests.testlib.system.licensing.license_management import (  # type: ignore[import-untyped, unused-ignore, import-not-found]
            read_license_state,
        )
        from tests.testlib.system.licensing.trial_mode import (  # type: ignore[import-untyped, unused-ignore, import-not-found]
            read_trial_start,
            trial_mode_selection_enabled,
        )

        with trial_mode_selection_enabled(base_site):
            # The site stores the trial start in whole seconds.
            upgrade_started = datetime.now(tz=UTC).replace(microsecond=0)
            target_site = update_site(
                base_site, get_target_package(target_edition), interactive_mode
            )

            assert read_license_state(target_site) is LicenseState.PENDING_SELECTION
            assert upgrade_started <= read_trial_start(target_site) <= datetime.now(tz=UTC)

    bulk_discover_and_schedule(target_site, hostname)

    check_services(target_site, hostname, base_data)

    check_errors_in_log_files(target_site)
    check_unseeded_config_warning(target_site, planted)
