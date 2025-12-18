#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Sequence

import pytest

from cmk.gui.fields.definitions import FOLDER_PATTERN
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.quick_setup.v0_unstable.definitions import UniqueBundleIDStr, UniqueFormSpecIDStr
from cmk.gui.quick_setup.v0_unstable.predefined import recaps, widgets
from cmk.gui.quick_setup.v0_unstable.predefined import validators as qs_validators
from cmk.gui.quick_setup.v0_unstable.setups import (
    CallableAction,
    ProgressLogger,
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionMode,
    QuickSetupBackgroundAction,
    QuickSetupBackgroundStageAction,
    QuickSetupStage,
    QuickSetupStageAction,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    FormSpecId,
    FormSpecWrapper,
)
from cmk.gui.watolib.configuration_bundle_store import ConfigBundleStore
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    String,
    validators,
)
from tests.testlib.unit.rest_api_client import ClientRegistry


def _make_action(
    return_value: str,
) -> CallableAction:
    """Helper function to create a callable action that returns a fixed URL."""

    def action(
        all_stages_form_data: ParsedFormData,
        mode: QuickSetupActionMode,
        _progress_logger: ProgressLogger,
        object_id: str | None,
        use_git: bool,
        pprint_value: bool,
    ) -> str:
        return return_value

    return action


def register_quick_setup(
    setup_stages: Sequence[Callable[[], QuickSetupStage]] | None = None,
    load_data: Callable[[str], ParsedFormData | None] = lambda _: None,
    actions: Sequence[QuickSetupAction] | None = None,
) -> None:
    if actions is None:
        actions = [
            QuickSetupAction(
                id=ActionId("save"),
                label="Complete",
                action=_make_action("http://save/url"),
                custom_validators=[],
            ),
            QuickSetupAction(
                id=ActionId("other_save"),
                label="Complete2: The Sequel",
                action=_make_action("http://other_save"),
                custom_validators=[],
            ),
        ]

    quick_setup_registry.register(
        QuickSetup(
            title="Quick Setup Test",
            id=QuickSetupId("quick_setup_test"),
            stages=setup_stages if setup_stages is not None else [],
            actions=actions,
            load_data=load_data,
        ),
    )


def test_get_quick_setup_mode_guided(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.get_overview_mode_or_guided_mode(
        quick_setup_id="quick_setup_test", mode="guided"
    )
    assert len(resp.json["overviews"]) == 1
    assert len(resp.json["stage"]["components"]) == 1
    assert resp.json["stage"]["actions"][0]["button"]["label"] == "Next"


def test_validate_retrieve_next(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[recaps.recaps_form_spec],
                        next_button_label="Next",
                    )
                ],
            ),
            lambda: QuickSetupStage(
                title="stage2",
                configure_components=[],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_stage_action(
        quick_setup_id="quick_setup_test",
        stage_action_id="action",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "test_account_name"}}}],
    )
    assert resp.json["validation_errors"] is None
    assert len(resp.json["stage_recap"]) == 1

    resp = clients.QuickSetup.get_stage_structure(
        quick_setup_id="quick_setup_test",
        stage_index=1,
    )
    assert resp.json["actions"][0]["button"]["label"] == "Next"


def _form_spec_extra_validate(
    _quick_setup_id: QuickSetupId,
    _stages: ParsedFormData,
    _progress_logger: ProgressLogger,
) -> GeneralStageErrors:
    return ["this is a general error", "and another one"]


def test_failing_validate(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[_form_spec_extra_validate],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_stage_action(
        quick_setup_id="quick_setup_test",
        stage_action_id="action",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: 5}}}],
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["validation_errors"] == {
        "stage_index": 0,
        "formspec_errors": {
            "formspec_unique_id": [
                {
                    "location": [UniqueBundleIDStr],
                    "message": "Invalid string",
                    "replacement_value": "",
                },
            ],
        },
        "stage_errors": [],
    }


def test_failing_validate_host_path(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    FormSpecWrapper(
                        id=FormSpecId("host_data"),
                        form_spec=Dictionary(
                            elements={
                                "host_path": DictElement(
                                    parameter_form=String(
                                        title=Title("Host path"),
                                        custom_validate=(
                                            validators.LengthInRange(min_value=1),
                                            validators.MatchRegex(FOLDER_PATTERN),
                                        ),
                                    ),
                                    required=True,
                                ),
                            }
                        ),
                    ),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[_form_spec_extra_validate],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_stage_action(
        quick_setup_id="quick_setup_test",
        stage_action_id="action",
        stages=[{"form_data": {"host_data": {"host_path": "#invalid_host_path#"}}}],
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["validation_errors"] == {
        "stage_index": 0,
        "formspec_errors": {
            "host_data": [
                {
                    "location": ["host_path"],
                    "message": "Your input does not match the required format '^(?:(?:[~\\\\\\/]|(?:[~\\\\\\/][-_ a-zA-Z0-9.]+)+[~\\\\\\/]?)|[0-9a-fA-F]{32})$'.",
                    "replacement_value": "#invalid_host_path#",
                },
            ],
        },
        "stage_errors": [],
    }


def test_quick_setup_save(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_quick_setup_action(
        quick_setup_id="quick_setup_test",
        payload={"button_id": "save", "stages": []},
    )
    resp.assert_status_code(201)
    assert resp.json["redirect_url"] == "http://save/url"


def test_quick_setup_save_action_exists(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    clients.QuickSetup.run_quick_setup_action(
        quick_setup_id="quick_setup_test",
        payload={"button_id": "some_nonexistent_id", "stages": []},
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.parametrize(
    "ident,is_valid",
    [
        pytest.param(
            "letters_underscores_and_digits_123", True, id="Letters, underscores, and digits"
        ),
        pytest.param("Letters-and-dashes", True, id="Letters and dashes"),
        pytest.param("All-valid_characters-123", True, id="All valid characters"),
        pytest.param("begin_with_letters", True, id="Begin with letters"),
        pytest.param("Begin_with_capital_letters", True, id="Begin with capital letters"),
        pytest.param("_begin_with_underscore", True, id="Begin with underscore"),
        pytest.param("123_begin_with_digit", False, id="Begin with digit"),
        pytest.param("-begin_with_dash", False, id="Begin with dash"),
        pytest.param("invalid$char", False, id="Invalid character"),
        pytest.param("Contain spaces", False, id="Contain spaces"),
    ],
)
def test_id_validation(ident: str, is_valid: bool) -> None:
    """test_id_validation

    The ID must accept
        - letters
        - digits
        - dash
        - underscore

    The ID must start with a letter or underscore.
    """
    regex = widgets.ID_VALIDATION_REGEX
    if is_valid:
        assert regex.match(ident)
    else:
        assert not regex.match(ident)


def test_unique_id_must_be_unique(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ConfigBundleStore, "load_for_reading", lambda _: {"I_should_be_unique": {}})

    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[qs_validators.validate_unique_id],
                        recap=[recaps.recaps_form_spec],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_stage_action(
        quick_setup_id="quick_setup_test",
        stage_action_id="action",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "I_should_be_unique"}}}],
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert len(resp.json["validation_errors"]["stage_errors"]) == 1


def test_get_quick_setup_mode_overview(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                sub_title="1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
            lambda: QuickSetupStage(
                title="stage2",
                sub_title="2",
                configure_components=[],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.get_overview_mode_or_guided_mode(
        quick_setup_id="quick_setup_test", mode="overview"
    )
    assert len(resp.json["stages"]) == 2
    assert set(resp.json["stages"][0]) == {
        "title",
        "sub_title",
        "components",
        "actions",
        "prev_button",
    }


def test_get_quick_setup_overview_prefilled(clients: ClientRegistry) -> None:
    def load_data(obj_id: str) -> ParsedFormData | None:
        return {
            "obj1": {FormSpecId(UniqueFormSpecIDStr): {UniqueBundleIDStr: "foo"}},
            "obj2": {FormSpecId(UniqueFormSpecIDStr): {UniqueBundleIDStr: "bar"}},
        }.get(obj_id)

    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                sub_title="1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
        load_data=load_data,
    )
    resp = clients.QuickSetup.get_overview_mode_or_guided_mode(
        quick_setup_id="quick_setup_test", mode="overview", object_id="obj1"
    )
    assert (
        resp.json["stages"][0]["components"][0]["form_spec"]["spec"]["elements"][0]["default_value"]
        == "foo"
    )

    resp = clients.QuickSetup.get_overview_mode_or_guided_mode(
        quick_setup_id="quick_setup_test", mode="overview", object_id="obj2"
    )
    assert (
        resp.json["stages"][0]["components"][0]["form_spec"]["spec"]["elements"][0]["default_value"]
        == "bar"
    )

    resp = clients.QuickSetup.get_overview_mode_or_guided_mode(
        quick_setup_id="quick_setup_test", mode="overview", object_id="obj3", expect_ok=False
    )
    resp.assert_status_code(404)


def test_quick_setup_edit(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.edit_quick_setup(
        quick_setup_id="quick_setup_test",
        payload={"button_id": "save", "stages": []},
        object_id="obj1",
    )
    resp.assert_status_code(201)
    assert resp.json["redirect_url"] == "http://save/url"


@pytest.mark.parametrize(
    "post_data, expected_errors",
    [
        (
            [
                {"form_data": {"id_1": "too_short"}},
                {"form_data": {"id_2": "this_is_too_long"}},
            ],
            [
                {
                    "stage_index": 0,
                    "formspec_errors": {
                        "id_1": [
                            {
                                "message": "The minimum allowed length is 10.",
                                "replacement_value": "too_short",
                                "location": [],
                            }
                        ],
                    },
                    "stage_errors": [],
                },
                {
                    "stage_index": 1,
                    "formspec_errors": {
                        "id_2": [
                            {
                                "message": "The maximum allowed length is 10.",
                                "replacement_value": "this_is_too_long",
                                "location": [],
                            }
                        ]
                    },
                    "stage_errors": [],
                },
                {
                    "stage_index": None,
                    "formspec_errors": {},
                    "stage_errors": [
                        "Stages 1, 2 contain invalid form data. Please correct them and try again."
                    ],
                },
            ],
        ),
        (
            [
                {"form_data": {"invalid_id_1": "doesnt_matter"}},
                {"form_data": {"invalid_id_2": "doesnt_matter"}},
            ],
            [
                {
                    "stage_index": 0,
                    "formspec_errors": {},
                    "stage_errors": ["Formspec id 'invalid_id_1' not found"],
                },
                {
                    "stage_index": 1,
                    "formspec_errors": {},
                    "stage_errors": ["Formspec id 'invalid_id_2' not found"],
                },
                {
                    "stage_index": None,
                    "formspec_errors": {},
                    "stage_errors": [
                        "Stages 1, 2 contain invalid form data. Please correct them and try again."
                    ],
                },
            ],
        ),
        (
            [
                {"form_data": {"id_1": "valid_data"}},
                {"form_data": {"id_2": "valid_data"}},
            ],
            [
                {
                    "formspec_errors": {},
                    "stage_errors": ["this is a general error", "and another one"],
                    "stage_index": None,
                }
            ],
        ),
    ],
    ids=["formspec_validators", "invalid_formspec_keys", "custom_validator_fail"],
)
def test_validation_on_save_all(
    clients: ClientRegistry, post_data: list, expected_errors: list
) -> None:
    register_quick_setup(
        actions=[
            QuickSetupAction(
                id=ActionId("save"),
                label="Complete",
                action=_make_action("http://save/url"),
                custom_validators=[_form_spec_extra_validate],
            ),
        ],
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    FormSpecWrapper(
                        id=FormSpecId("id_1"),
                        form_spec=String(
                            title=Title("string_id_1"),
                            custom_validate=(validators.LengthInRange(min_value=10),),
                        ),
                    ),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
            lambda: QuickSetupStage(
                title="stage2",
                configure_components=[
                    FormSpecWrapper(
                        id=FormSpecId("id_2"),
                        form_spec=String(
                            title=Title("string_id_2"),
                            custom_validate=(validators.LengthInRange(max_value=10),),
                        ),
                    ),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[],
                        next_button_label="Next",
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_quick_setup_action(
        quick_setup_id="quick_setup_test",
        payload={
            "button_id": "save",
            "stages": post_data,
        },
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["all_stage_errors"] == expected_errors


class TestValidateAndRetrieveNext:
    @pytest.mark.usefixtures("inline_background_jobs")
    def test_openapi_background_job_action(self, clients: ClientRegistry) -> None:
        register_quick_setup(
            setup_stages=[
                lambda: QuickSetupStage(
                    title="stage1",
                    configure_components=[
                        widgets.unique_id_formspec_wrapper(Title("account name")),
                    ],
                    actions=[
                        QuickSetupBackgroundStageAction(
                            id=ActionId("action"),
                            custom_validators=[],
                            recap=[recaps.recaps_form_spec],
                            next_button_label="Next",
                        )
                    ],
                ),
                lambda: QuickSetupStage(
                    title="stage2",
                    configure_components=[],
                    actions=[
                        QuickSetupStageAction(
                            id=ActionId("action"),
                            custom_validators=[],
                            recap=[],
                            next_button_label="Next",
                        )
                    ],
                ),
            ],
        )
        # the underlying background actually fails as it doesn't have access to the registered
        # quick setup defined in this scope
        resp = clients.QuickSetup.run_stage_action(
            quick_setup_id="quick_setup_test",
            stage_action_id="action",
            stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "test_account_name"}}}],
            follow_redirects=False,
        )
        assert "objects/background_job" in resp.headers["Location"]


class TestCompleteAction:
    @pytest.mark.usefixtures("inline_background_jobs")
    def test_openapi_background_job_setup_action(self, clients: ClientRegistry) -> None:
        register_quick_setup(
            actions=[
                QuickSetupBackgroundAction(
                    id=ActionId("save"),
                    label="Complete",
                    action=_make_action("http://save/url"),
                    custom_validators=[],
                ),
            ],
            setup_stages=[
                lambda: QuickSetupStage(
                    title="stage1",
                    configure_components=[
                        FormSpecWrapper(
                            id=FormSpecId("id_1"),
                            form_spec=String(
                                title=Title("string_id_1"),
                                custom_validate=(validators.LengthInRange(min_value=10),),
                            ),
                        ),
                    ],
                    actions=[
                        QuickSetupStageAction(
                            id=ActionId("action"),
                            custom_validators=[],
                            recap=[],
                            next_button_label="Next",
                        )
                    ],
                ),
            ],
        )
        # the underlying background actually fails as it doesn't have access to the registered
        # quick setup defined in this scope
        resp = clients.QuickSetup.run_quick_setup_action(
            quick_setup_id="quick_setup_test",
            payload={
                "button_id": "save",
                "stages": [
                    {"form_data": {"id_1": "valid_data"}},
                ],
            },
            follow_redirects=False,
            expect_ok=True,
        )
        assert "objects/background_job" in resp.headers["Location"]


@pytest.mark.parametrize(
    "perm",
    [(["general.use"]), (None)],
)
def test_validate_permission(clients: ClientRegistry, perm: list[str] | None) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[recaps.recaps_form_spec],
                        next_button_label="Next",
                        permissions=perm,
                    )
                ],
            ),
        ],
    )
    res = clients.QuickSetup.run_stage_action(
        quick_setup_id="quick_setup_test",
        stage_action_id="action",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "test_account_name"}}}],
    )
    assert res.json["validation_errors"] is None
    assert res.json["background_job_exception"] is None
    assert res.json["stage_recap"][0]["id"] == "formspec_unique_id"
    assert res.json["stage_recap"][0]["form_spec"]["data"]["bundle_id"] == "test_account_name"


def test_fail_validate_permission(clients: ClientRegistry) -> None:
    register_quick_setup(
        setup_stages=[
            lambda: QuickSetupStage(
                title="stage1",
                configure_components=[
                    widgets.unique_id_formspec_wrapper(Title("account name")),
                ],
                actions=[
                    QuickSetupStageAction(
                        id=ActionId("action"),
                        custom_validators=[],
                        recap=[recaps.recaps_form_spec],
                        next_button_label="Next",
                        permissions=["impossible_permisson"],
                    )
                ],
            ),
        ],
    )
    resp = clients.QuickSetup.run_stage_action(
        quick_setup_id="quick_setup_test",
        stage_action_id="action",
        stages=[{"form_data": {UniqueFormSpecIDStr: {UniqueBundleIDStr: "test_account_name"}}}],
        expect_ok=False,
    )

    assert resp.status_code == 403
    assert resp.json["title"] == "Action not allowed"
    assert (
        resp.json["detail"]
        == "Action with id 'action' requires 'impossible_permisson' permissions."
    )
