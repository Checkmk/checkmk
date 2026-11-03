#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.config_setups.azure_v2.stages import action
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSHostPath,
    QSSiteSelection,
    UniqueBundleIDStr,
    UniqueFormSpecIDStr,
)
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode, QuickSetupContext
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.watolib.configuration_bundle_store import BundleId
from cmk.gui.watolib.configuration_bundles import identify_single_bundle_references
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from tests.testlib.unit.gui.web_test_app import SetConfig

_BUNDLE_ID = BundleId("my_azure_config")

_FORM_DATA: ParsedFormData = {
    FormSpecId(UniqueFormSpecIDStr): {UniqueBundleIDStr: _BUNDLE_ID},
    FormSpecId("credentials"): {
        "subscription": ("all_subscriptions", None),
        "tenant_name": "my_tenant",
        "tenant": "my_tenant_id",
        "client": "my_client_id",
        "secret": (
            "cmk_postprocessed",
            "explicit_password",
            ("uuid-azure-secret", "my_client_secret"),
        ),
        "authority": "global_",
    },
    FormSpecId("host_data"): {QSHostName: "azure_host", QSHostPath: "azure_folder"},
    # The Quick Setup skips the service discovery for a remote site without replication.
    FormSpecId("site"): {QSSiteSelection: "remote"},
    # This edition does not offer the field, so the value must not have any effect.
    FormSpecId("configure_services_to_monitor"): {
        "services": [],
        "otel_resource_types": ["Microsoft_Network_slash_publicIPAddresses"],
    },
}


@pytest.mark.usefixtures("with_admin_login", "mock_password_file_regeneration")
def test_without_telemetry_only_the_special_agent_rule_is_saved(set_config: SetConfig) -> None:
    remote_site = {
        **active_config.sites[omd_site()],
        "id": "remote",
        "socket": ("tcp", {}),
        "replication": None,
    }
    with set_config(sites={**active_config.sites, "remote": remote_site}):
        ctx = QuickSetupContext.from_config(active_config, user)

        action(_FORM_DATA, QuickSetupActionMode.SAVE, InfoLogger(), None, ctx)

    references = identify_single_bundle_references(
        ctx.tree, _BUNDLE_ID, acting_user=user, program_id=PROGRAM_ID_QUICK_SETUP
    )
    assert [rule.ruleset.name for rule in references.rules or ()] == ["special_agents:azure_v2"]
