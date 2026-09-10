#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, VisitorOptions
from cmk.gui.quick_setup.config_setups.kubernetes.connection_forms import connection_configuration
from cmk.gui.quick_setup.config_setups.kubernetes.settings import ADVANCED, CONNECTION, PULL_URL
from cmk.gui.quick_setup.config_setups.kubernetes.stages import (
    completion_action,
    configure_cluster,
    configure_host,
    configure_pull_url,
    prepare_deployment,
    quick_setup_kubernetes,
)
from cmk.gui.quick_setup.handlers.setup import quick_setup_guided_mode
from cmk.gui.quick_setup.handlers.stage import get_stage_structure
from cmk.gui.quick_setup.handlers.utils import stage_applicability_and_form_data
from cmk.gui.quick_setup.v0_unstable.definitions import QSSiteSelection
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupBackgroundStageAction
from cmk.gui.quick_setup.v0_unstable.type_defs import RawFormData
from cmk.gui.quick_setup.v0_unstable.widgets import Collapsible
from cmk.licensing.basics.options import OptionName
from cmk.licensing.registry import is_option_enabled
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoice
from cmk.utils import paths

pytestmark = pytest.mark.usefixtures("with_admin_login")


@pytest.mark.parametrize(
    "stage_index, expected_label",
    [
        pytest.param(0, None, id="cluster-is-first"),
        pytest.param(1, "Back", id="host-to-cluster"),
        pytest.param(2, "Back", id="deployment-to-host"),
        pytest.param(3, "Back", id="pull-url-to-deployment"),
    ],
)
def test_stage_responses_offer_back_navigation_after_first_stage(
    stage_index: int, expected_label: str | None
) -> None:
    response = get_stage_structure(quick_setup_kubernetes.stages[stage_index]())

    assert (response.prev_button.label if response.prev_button else None) == expected_label


def test_advanced_options_are_collapsed_but_part_of_form_validation() -> None:
    stage = configure_cluster()
    components = stage.configure_components
    assert not callable(components)
    assert any(isinstance(component, Collapsible) for component in components)
    assert ADVANCED in build_formspec_map_from_stages([stage])


def test_pull_url_is_only_in_the_final_stage() -> None:
    assert PULL_URL not in build_formspec_map_from_stages(
        [configure_cluster(), configure_host(), prepare_deployment()]
    )
    assert set(build_formspec_map_from_stages([configure_pull_url()])) == {PULL_URL}


def test_deployment_action_authorizes_centrally_and_checks_host_permissions() -> None:
    (action,) = prepare_deployment().actions
    assert isinstance(action, QuickSetupBackgroundStageAction)
    assert action.target_site_formspec_key is None
    assert action.permissions and "wato.manage_hosts" in action.permissions
    # The central recap validates immediately before requesting site-local credentials.
    assert not list(action.custom_validators)
    assert list(configure_host().actions[0].custom_validators)
    assert list(completion_action().custom_validators)
    assert completion_action().permissions


def test_deployment_stage_applies_the_sites_push_capability() -> None:
    forms = build_formspec_map_from_stages([prepare_deployment()])
    schema, _values = get_visitor(
        forms[CONNECTION], VisitorOptions(migrate_values=True, mask_values=False)
    ).to_vue(DEFAULT_VALUE)

    assert isinstance(schema, CascadingSingleChoice)
    assert ("push" in {element.name for element in schema.elements}) == is_option_enabled(
        paths.omd_root, OptionName.AGENT_REGISTRATION
    )


def test_pull_url_offers_a_background_connection_test_and_explicit_skip() -> None:
    stage = configure_pull_url()
    test_action, skip_action = stage.actions

    assert [action.button.label for action in get_stage_structure(stage).actions] == [
        "Test connection",
        "Skip test",
    ]
    assert isinstance(test_action, QuickSetupBackgroundStageAction)
    assert test_action.target_site_formspec_key == QSSiteSelection
    assert list(test_action.custom_validators)
    assert not isinstance(skip_action, QuickSetupBackgroundStageAction)
    assert not list(skip_action.custom_validators)


@pytest.mark.parametrize(
    "mode,expected",
    [
        pytest.param("push", False, id="push"),
        pytest.param("pull", True, id="pull"),
    ],
)
def test_registered_final_url_stage_follows_connection_mode(mode: str, expected: bool) -> None:
    forms = {
        CONNECTION: connection_configuration(
            receiver_host="monitor", shared_secret="secret", push_supported=True
        )
    }
    schema, _value = get_visitor(
        forms[CONNECTION], VisitorOptions(migrate_values=True, mask_values=False)
    ).to_vue(DEFAULT_VALUE)
    assert isinstance(schema, CascadingSingleChoice)
    connection_data = next(
        element.default_value for element in schema.elements if element.name == mode
    )

    applicable, _filtered = stage_applicability_and_form_data(
        quick_setup_kubernetes.stages,
        [RawFormData({}), RawFormData({}), RawFormData({CONNECTION: [mode, connection_data]})],
        forms,
    )

    assert applicable == [True, True, True, expected]


def test_switching_to_push_discards_a_previous_pull_url() -> None:
    forms = {
        CONNECTION: connection_configuration(
            receiver_host="monitor", shared_secret="secret", push_supported=True
        )
    }
    _schema, push_defaults = get_visitor(
        forms[CONNECTION], VisitorOptions(migrate_values=True, mask_values=False)
    ).to_vue(DEFAULT_VALUE)

    _applicable, filtered = stage_applicability_and_form_data(
        quick_setup_kubernetes.stages,
        [
            RawFormData({}),
            RawFormData({}),
            RawFormData({CONNECTION: push_defaults}),
            RawFormData({PULL_URL: {"base_url": "https://previous-agent"}}),
        ],
        forms,
    )

    assert filtered[-1] == {}


def test_initial_guided_setup_does_not_show_the_pull_url_stage() -> None:
    overview = quick_setup_guided_mode(quick_setup_kubernetes, None)

    assert [stage.is_applicable for stage in overview.overviews] == [True, True, True, False]
