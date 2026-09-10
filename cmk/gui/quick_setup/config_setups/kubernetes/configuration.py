#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from copy import deepcopy

from cmk.gui.quick_setup.v0_unstable.predefined import complete
from cmk.gui.watolib.configuration_bundle_store import BundleId
from cmk.gui.watolib.configuration_bundles import CreateBundleEntities, CreateDCDConnection
from cmk.password_store.v1_unstable import Secret

from .constants import QUICK_SETUP_ID


def with_dcd_host_deletion(
    connections: Sequence[CreateDCDConnection],
) -> list[CreateDCDConnection]:
    """Enable cleanup while preserving the hook's source filters and timing safeguards."""
    result = deepcopy(list(connections))
    for connection in result:
        _connector_type, connector_spec = connection["spec"]["connector"]
        for creation_rule in connector_spec["creation_rules"]:
            creation_rule["delete_hosts"] = True
    return result


def pull_configuration(
    *,
    bundle_id: BundleId,
    host_name: str,
    host_path: str,
    site_id: str,
    base_url: str,
    shared_secret: str,
) -> CreateBundleEntities:
    """Prepare the pull rule and its password for saving with the configuration bundle.

    The caller supplies the same secret used for deployment, validates the base URL,
    and requires wato.edit_all_passwords. Bundle creation handles ID collisions and ownership.
    """
    if not shared_secret:
        raise ValueError("The pull shared secret must not be empty")

    password_id = f"{bundle_id}_pull_secret"
    return CreateBundleEntities(
        passwords=complete.create_passwords({password_id: Secret(shared_secret)}, bundle_id),
        rules=[
            complete.create_rule(
                params={
                    "url": base_url.rstrip("/"),
                    "shared_secret": (
                        "cmk_postprocessed",
                        "stored_password",
                        (password_id, ""),
                    ),
                    "verify_cert": True,
                },
                host_name=host_name,
                host_path=host_path,
                rulespec_name=QUICK_SETUP_ID,
                bundle_id=bundle_id,
                site_id=site_id,
            )
        ],
    )
