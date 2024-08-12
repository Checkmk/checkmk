#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from cmk.gui.quick_setup.predefined import unique_id_formspec_wrapper
from cmk.gui.quick_setup.to_frontend import recaps_form_spec, validate_unique_id
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import UniqueBundleIDStr, UniqueFormSpecIDStr
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.watolib.configuration_bundles import ConfigBundleStore

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec


def register_quick_setup(setup_stages: Sequence[QuickSetupStage] | None = None) -> None:
    quick_setup_registry.register(
        QuickSetup(
            title="Quick Setup Test",
            id=QuickSetupId("quick_setup_test"),
            stages=setup_stages if setup_stages is not None else [],
            save_action=lambda stages: "http://save/url",
            button_complete_label="Complete",
        ),
    )


def test_quick_setup_get(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                custom_validators=[],
                recap=[],
                button_label="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.get_overview_and_first_stage("quick_setup_test")
    assert len(resp.json["overviews"]) == 1
    assert len(resp.json["stage"]["next_stage_structure"]["components"]) == 1
    assert resp.json["stage"]["next_stage_structure"]["button_label"] == "Next"


def test_validate_retrieve_next(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                custom_validators=[],
                recap=[recaps_form_spec],
                button_label="Next",
            ),
            QuickSetupStage(
                title="stage2",
                configure_components=[],
                custom_validators=[],
                recap=[],
                button_label="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "test_account_name"}}}],
    )
    assert resp.json["errors"] is None
    assert len(resp.json["stage_recap"]) == 1
    assert resp.json["next_stage_structure"]["button_label"] == "Next"


def _form_spec_extra_validate(
    _stages: ParsedFormData, formspec_map: Mapping[FormSpecId, FormSpec]
) -> GeneralStageErrors:
    return ["this is a general error", "and another one"]


def test_failing_validate(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                custom_validators=[_form_spec_extra_validate],
                recap=[],
                button_label="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: 5}}}],
        expect_ok=False,
    )
    assert resp.assert_status_code(400)
    assert resp.json["errors"] == {
        "formspec_errors": {
            "formspec_unique_id": [
                {
                    "location": [UniqueBundleIDStr],
                    "message": "Invalid string",
                    "invalid_value": 5,
                },
            ],
        },
        "stage_errors": [],
    }
    assert resp.json["next_stage_structure"] is None


def test_quick_setup_save(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                custom_validators=[],
                recap=[],
                button_label="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.complete_quick_setup(
        quick_setup_id="quick_setup_test",
        payload={"stages": []},
    )
    resp.assert_status_code(201)
    assert resp.json == {"redirect_url": "http://save/url"}


def test_unique_id_must_be_unique(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ConfigBundleStore, "load_for_reading", lambda _: {"I should be unique": {}})

    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                custom_validators=[validate_unique_id],
                recap=[recaps_form_spec],
                button_label="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "I should be unique"}}}],
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert len(resp.json["errors"]["stage_errors"]) == 1
