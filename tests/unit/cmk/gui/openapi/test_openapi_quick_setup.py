#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from tests.testlib.rest_api_client import ClientRegistry

from cmk.utils.quick_setup.definitions import (
    quick_setup_registry,
    QuickSetup,
    QuickSetupId,
    QuickSetupStage,
    StageId,
)
from cmk.utils.quick_setup.widgets import FormSpecId, FormSpecWrapper

from cmk.gui.quick_setup.to_frontend import form_spec_recap, form_spec_validate

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FieldSize, String, validators


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
                    FormSpecWrapper(
                        id=FormSpecId("wrapper_id"),
                        form_spec=Dictionary(
                            elements={
                                "account_name": DictElement(
                                    parameter_form=String(
                                        title=Title("test account name"),
                                        field_size=FieldSize.MEDIUM,
                                        custom_validate=(validators.LengthInRange(min_value=1),),
                                    ),
                                    required=True,
                                )
                            }
                        ),
                    ),
                ],
                validators=[form_spec_validate],
                recap=[],
            ),
        ],
    )
    resp = clients.QuickSetup.get_overview_and_first_stage("quick_setup_test")
    assert len(resp.json["overviews"]) == 1
    assert len(resp.json["stage"]["components"]) == 1


def test_validate_retrieve_next(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                stage_id=StageId(1),
                title="stage1",
                configure_components=[
                    FormSpecWrapper(
                        id=FormSpecId("wrapper_id"),
                        form_spec=Dictionary(
                            elements={
                                "account_name": DictElement(
                                    parameter_form=String(
                                        title=Title("test account name"),
                                        field_size=FieldSize.MEDIUM,
                                        custom_validate=(validators.LengthInRange(min_value=1),),
                                    ),
                                    required=True,
                                )
                            }
                        ),
                    ),
                ],
                validators=[form_spec_validate],
                recap=[form_spec_recap],
            ),
            QuickSetupStage(
                stage_id=StageId(2),
                title="stage2",
                configure_components=[],
                validators=[form_spec_validate],
                recap=[],
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[
            {"stage_id": 1, "form_data": {"wrapper_id": {}}},
        ],
    )
    assert resp.json["stage_id"] == 2
    assert len(resp.json["validation_errors"]) == 0
    assert len(resp.json["stage_recap"]) == 1


def test_failing_validate(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            QuickSetupStage(
                stage_id=StageId(1),
                title="stage2",
                configure_components=[],
                validators=[form_spec_validate],
                recap=[],
            ),
        ],
    )
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="quick_setup_test",
        stages=[
            {"stage_id": 1, "form_data": {"unknown_id_1": {}, "unknown_id_2": {}}},
        ],
        expect_ok=False,
    )
    assert resp.assert_status_code(400)
    assert resp.json["stage_id"] == 1
    assert resp.json["validation_errors"] == ["'unknown_id_1'", "'unknown_id_2'"]


def test_quick_setup_save(clients: ClientRegistry) -> None:
    register_quick_setup()
    resp = clients.QuickSetup.complete_quick_setup(
        quick_setup_id="quick_setup_test",
        payload={"stages": []},
    )
    resp.assert_status_code(201)
    assert resp.json == {"redirect_url": "http://save/url"}
