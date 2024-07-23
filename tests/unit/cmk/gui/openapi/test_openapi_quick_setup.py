#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from cmk.utils.quick_setup.definitions import (
    FormData,
    GeneralStageErrors,
    quick_setup_registry,
    QuickSetup,
    QuickSetupId,
    QuickSetupStage,
    QuickSetupValidationError,
    StageId,
    UniqueBundleIDStr,
    UniqueFormSpecIDStr,
    ValidationErrorMap,
)
from cmk.utils.quick_setup.widgets import FormSpecId

from cmk.gui.quick_setup.predefined import unique_id_formspec_wrapper
from cmk.gui.quick_setup.to_frontend import form_spec_recaps, form_spec_validate, validate_unique_id
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
        ),
    )


def test_quick_setup_get(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                stage_id=StageId(1),
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                validators=[form_spec_validate],
                recap=[],
                button_txt="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.get_overview_and_first_stage("quick_setup_test")
    assert len(resp.json["overviews"]) == 1
    assert len(resp.json["stage"]["components"]) == 1
    assert resp.json["stage"]["button_txt"] == "Next"


def test_validate_retrieve_next(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                stage_id=StageId(1),
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                validators=[form_spec_validate],
                recap=[form_spec_recaps],
                button_txt="Next",
            ),
            QuickSetupStage(
                stage_id=StageId(2),
                title="stage2",
                configure_components=[],
                validators=[form_spec_validate],
                recap=[],
                button_txt="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[
            {
                "stage_id": 1,
                "form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "test_account_name"}},
            },
        ],
    )
    assert resp.json["stage_id"] == 2
    assert resp.json["errors"] is None
    assert len(resp.json["stage_recap"]) == 1
    assert resp.json["button_txt"] == "Next"


def _form_spec_extra_validate(
    _stages: Sequence[FormData], formspec_map: Mapping[FormSpecId, FormSpec]
) -> tuple[ValidationErrorMap, GeneralStageErrors]:
    return {
        FormSpecId(form_spec_id): [
            QuickSetupValidationError(
                location=[],
                message="this is a simulated error",
                invalid_value="invalid_data",
            ),
        ]
        for form_spec_id, _ in formspec_map.items()
    }, ["this is a general error", "and another one"]


def test_failing_validate(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                stage_id=StageId(1),
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                validators=[form_spec_validate, _form_spec_extra_validate],
                recap=[],
                button_txt="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[
            {
                "stage_id": 1,
                "form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: 5}},
            },
        ],
        expect_ok=False,
    )
    assert resp.assert_status_code(400)
    assert resp.json["stage_id"] == 1
    assert resp.json["errors"] == {
        "formspec_errors": {
            "formspec_unique_id": [
                {
                    "location": [UniqueBundleIDStr],
                    "message": "Invalid string",
                    "invalid_value": 5,
                },
                {
                    "location": [],
                    "message": "this is a simulated error",
                    "invalid_value": "invalid_data",
                },
            ],
        },
        "stage_errors": ["this is a general error", "and another one"],
    }
    assert resp.json["button_txt"] is None


def test_quick_setup_save(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                stage_id=StageId(1),
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                validators=[],
                recap=[],
                button_txt="Next",
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
                stage_id=StageId(1),
                title="stage1",
                configure_components=[
                    unique_id_formspec_wrapper(Title("account name")),
                ],
                validators=[validate_unique_id],
                recap=[form_spec_recaps],
                button_txt="Next",
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[
            {
                "stage_id": 1,
                "form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "I should be unique"}},
            },
        ],
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert len(resp.json["errors"]["stage_errors"]) == 1
