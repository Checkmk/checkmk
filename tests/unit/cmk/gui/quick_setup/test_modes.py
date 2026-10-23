#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.version import Edition
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.quick_setup._modes import (
    MainModuleQuickSetupKubernetes,
    ModeConfigurationBundle,
    ModeEditConfigurationBundles,
    ModeQuickSetupSpecialAgent,
)
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.type_defs import QuickSetupId
from cmk.gui.rule_specs.loader import LoadedRuleSpec
from cmk.gui.rule_specs.registering import register_plugin
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic
from tests.testlib.common.utils import reset_registries
from tests.unit.cmk.gui.quick_setup.factories import QuickSetupFactory


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
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )

    # The fix ensures self._bundle is never accessed when self._existing_bundle is False.
    assert not hasattr(mode, "_bundle")


_TEST_SPECIAL_AGENT = "special_agents:quick_setup_test"


@pytest.fixture(name="special_agent_with_quick_setup")
def fixture_special_agent_with_quick_setup() -> Iterator[str]:
    """A special agent ruleset with a configuration Quick Setup, as plug-ins provide them"""
    yield from _special_agent_with_quick_setup(is_deprecated=False)


@pytest.fixture(name="deprecated_special_agent_with_quick_setup")
def fixture_deprecated_special_agent_with_quick_setup() -> Iterator[str]:
    yield from _special_agent_with_quick_setup(is_deprecated=True)


def _special_agent_with_quick_setup(*, is_deprecated: bool) -> Iterator[str]:
    with (
        reset_registries([rulespec_registry]),
        reset_registries([rulespec_group_registry]),
        reset_registries([quick_setup_registry]),
    ):
        register_plugin(
            rulespec_registry,
            LoadedRuleSpec(
                rule_spec=SpecialAgent(
                    name="quick_setup_test",
                    title=Title("Quick setup test"),
                    topic=Topic.GENERAL,
                    parameter_form=lambda: Dictionary(elements={}),
                    is_deprecated=is_deprecated,
                ),
                edition_only=Edition.COMMUNITY,
            ),
        )
        quick_setup_registry.register(QuickSetupFactory.build(id=QuickSetupId(_TEST_SPECIAL_AGENT)))
        yield _TEST_SPECIAL_AGENT


@pytest.mark.usefixtures("with_admin_login")
def test_special_agent_configuration_titles_follow_the_rulespec(
    test_edition: Edition, special_agent_with_quick_setup: str
) -> None:
    request.set_var("varname", special_agent_with_quick_setup)
    context = PageContext(
        config=active_config,
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(active_config, all_permissions()),
    )
    listing = ModeEditConfigurationBundles(test_edition, context)
    setup = ModeQuickSetupSpecialAgent(test_edition, context)

    assert listing.title() == "Quick setup test"
    assert setup.title() == "Add Quick setup test configuration"
    assert [str(item.title) for item in setup.breadcrumb()][-2:] == [
        "Quick setup test",
        "Add Quick setup test configuration",
    ]


def _page_context() -> PageContext:
    return PageContext(
        config=active_config,
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(active_config, all_permissions()),
    )


@pytest.mark.usefixtures("with_admin_login")
def test_add_configuration_is_blocked_for_deprecated_special_agent(
    test_edition: Edition, deprecated_special_agent_with_quick_setup: str
) -> None:
    request.set_var("varname", deprecated_special_agent_with_quick_setup)

    with pytest.raises(MKUserError, match="This Quick Setup is deprecated"):
        ModeQuickSetupSpecialAgent(test_edition, _page_context())


@pytest.mark.usefixtures("with_admin_login")
def test_add_configuration_menu_entry_is_disabled_for_deprecated_special_agent(
    test_edition: Edition, deprecated_special_agent_with_quick_setup: str
) -> None:
    request.set_var("varname", deprecated_special_agent_with_quick_setup)
    listing = ModeEditConfigurationBundles(test_edition, _page_context())

    menu = listing.page_menu(active_config, listing.breadcrumb())

    [entry] = [e for e in menu.shortcuts if e.title == "Add configuration"]
    assert not entry.is_enabled


@pytest.mark.usefixtures("with_admin_login")
def test_kubernetes_menu_links_to_the_registered_setup() -> None:
    entry = MainModuleQuickSetupKubernetes()

    assert entry.title == "Kubernetes"
    assert "special_agents%3Akube_v2" in entry.mode_or_url
    assert entry.may_see()
    assert entry.icon
