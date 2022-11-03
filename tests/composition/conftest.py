#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import os
import time
from pathlib import Path
from typing import Iterator

import pytest

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import current_branch_name
from tests.testlib.version import CMKVersion

from livestatus import SiteId

from cmk.utils.type_defs import UserId

from cmk.gui import key_mgmt

# pylint and isort don't agree on where to place the following imports so we are disabling pylint
from tests.composition.constants import (  # pylint: disable=ungrouped-imports
    SERVER_REL_MULTISITED_DIR,
    SIGNATURE_KEY_ID,
    SIGNATURE_KEY_NAME,
    SIGNATURE_KEY_PASSPHRASE,
    TEST_HOST_1,
)
from tests.composition.utils import get_package_type, wait_for_baking_job

site_number = 0


# Disable this. We have a site_factory instead.
@pytest.fixture(scope="module")
def site(request):
    pass


# The scope of the site factory is "module" to avoid that changing the site properties in a module
# may result in a test failing in another one
@pytest.fixture(scope="module")
def site_factory() -> Iterator[SiteFactory]:
    # Using a different site for every module to avoid having issues when saving the results for the
    # tests: if you call SiteFactory.save_results() twice with the same site_id, it will crash
    # because the results are already there.
    global site_number
    sf = SiteFactory(
        version=os.environ.get("VERSION", CMKVersion.DAILY),
        edition=os.environ.get("EDITION", CMKVersion.CEE),
        branch=os.environ.get("BRANCH") or current_branch_name(),
        prefix=f"comp_{site_number}_",
    )
    site_number += 1
    try:
        yield sf
    finally:
        sf.save_results()
        sf.cleanup()


@pytest.fixture(scope="module")
def central_site(site_factory: SiteFactory) -> Site:  # type:ignore[no-untyped-def]
    return site_factory.get_site("central")


@pytest.fixture(scope="module")
def signature_key(central_site: Site) -> key_mgmt.Key:
    return key_mgmt.generate_key(
        SIGNATURE_KEY_NAME, SIGNATURE_KEY_PASSPHRASE, UserId("me"), SiteId(central_site.id)
    )


@pytest.fixture(scope="module")
def bake_test_agent(signature_key: key_mgmt.Key, central_site: Site) -> tuple[str, Path]:

    write_signature_key_to_site(signature_key, central_site)

    # make agent updater rule, including the new certificate
    central_site.openapi.create_rule(
        "agent_config:cmk_update_agent",
        value={
            "activated": True,
            "signature_keys": [signature_key.certificate],
        },
    )

    # Add test host
    start_time = time.time()
    central_site.openapi.create_host(
        TEST_HOST_1,
        attributes={"ipaddress": central_site.http_address},
        bake_agent=True,
    )

    central_site.activate_changes_and_wait_for_core_reload()

    # A baking job just got triggered automatically after adding the host. wait for it to finish.
    wait_for_baking_job(central_site, start_time)

    central_site.openapi.sign_agents(key_id=SIGNATURE_KEY_ID, passphrase=SIGNATURE_KEY_PASSPHRASE)

    server_rel_hostlink_dir = Path("var", "check_mk", "agents", get_package_type(), "references")
    agent_path = central_site.resolve_path(server_rel_hostlink_dir / TEST_HOST_1)
    agent_hash = agent_path.name

    return agent_hash, agent_path


def write_signature_key_to_site(signature_key: key_mgmt.Key, central_site: Site) -> None:
    key_data = {SIGNATURE_KEY_ID: signature_key.dict()}
    signature_keys_text = f"agent_signature_keys.update({key_data!r})"
    central_site.write_text_file(
        str(Path(SERVER_REL_MULTISITED_DIR, "agent_signature_keys.mk")), signature_keys_text
    )
