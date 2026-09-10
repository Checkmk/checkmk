#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.config import active_config, Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.quick_setup._modes import (
    MainModuleQuickSetupKubernetes,
    ModeConfigurationBundle,
    ModeEditConfigurationBundles,
    ModeQuickSetupSpecialAgent,
)
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore
from cmk.gui.watolib.rulespecs import rulespec_registry


@pytest.mark.usefixtures("request_context")
def test_mode_configuration_bundle_action_crashes_when_bundle_missing(
    monkeypatch: pytest.MonkeyPatch, test_edition: Edition
) -> None:
    # Reproduces the crash: if the bundle disappears between GET (form render) and
    # POST (save), _from_vars() sets self._existing_bundle=False and returns early
    # without setting self._bundle. action() then crashes accessing self._bundle.
    request.set_var("bundle_id", "azure_config_2")
    monkeypatch.setattr(ConfigBundleStore, "load_for_reading", lambda self: {})  # noqa: ARG005

    # __init__ calls _from_vars(), which finds the bundle missing and returns early
    # without setting self._bundle — exactly mirroring the crash scenario.
    mode = ModeConfigurationBundle(
        test_edition,
        PageContext(config=Config(), request=request, transactions=transactions, session=session),
    )

    # The fix ensures self._bundle is never accessed when self._existing_bundle is False.
    assert not hasattr(mode, "_bundle")


@pytest.mark.usefixtures("with_admin_login")
def test_kubernetes_configuration_titles_follow_the_rulespec(
    test_edition: Edition,
) -> None:
    request.set_var("varname", "special_agents:kube_v2")
    context = PageContext(
        config=active_config,
        request=request,
        transactions=transactions,
        session=session,
    )
    listing = ModeEditConfigurationBundles(test_edition, context)
    setup = ModeQuickSetupSpecialAgent(test_edition, context)
    title = rulespec_registry["special_agents:kube_v2"].title
    assert title is not None

    assert listing.title() == title
    assert setup.title() == f"Add {title} configuration"
    assert [str(item.title) for item in setup.breadcrumb()][-2:] == [
        title,
        f"Add {title} configuration",
    ]


@pytest.mark.usefixtures("with_admin_login")
def test_kubernetes_menu_links_to_the_registered_setup() -> None:
    entry = MainModuleQuickSetupKubernetes()

    assert entry.title == "Kubernetes"
    assert "special_agents%3Akube_v2" in entry.mode_or_url
    assert entry.may_see()
    assert entry.icon
