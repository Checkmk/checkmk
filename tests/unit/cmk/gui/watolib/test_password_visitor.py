#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, Literal
from unittest.mock import ANY, patch

import pytest

from cmk.gui.form_specs import (
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.watolib.password_store import PasswordStore
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, migrate_to_password, Password
from cmk.utils.password_store import is_ad_hoc_password_id, PasswordConfig

PasswordOnDisk = tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]


@patch("cmk.gui.watolib.password_visitor.passwordstore_choices", return_value=[])
def test_password_encrypts_password(  # type: ignore[misc]
    patch_pwstore: None,  # noqa: ARG001
    request_context: None,  # noqa: ARG001
) -> None:
    password = "some_password"
    visitor = get_visitor(Password(), VisitorOptions(migrate_values=True, mask_values=False))
    _, frontend_value = visitor.to_vue(
        RawDiskData(("cmk_postprocessed", "explicit_password", ("", password)))
    )
    assert isinstance(frontend_value, tuple)

    assert not any(password in value for value in frontend_value if isinstance(value, str))

    disk_value = cast(PasswordOnDisk, visitor.to_disk(RawFrontendData(frontend_value)))
    assert disk_value[2][1] == password


@patch("cmk.gui.watolib.password_visitor.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    "value",
    [
        RawDiskData(("cmk_postprocessed", "explicit_password", ("", "some_password"))),
        RawFrontendData(("explicit_password", "", "some_password", False)),
    ],
)
def test_password_masks_password(  # type: ignore[misc]
    patch_pwstore: None,  # noqa: ARG001
    request_context: None,  # noqa: ARG001
    value: IncomingData,
) -> None:
    visitor = get_visitor(Password(), VisitorOptions(migrate_values=True, mask_values=True))
    _, _, (_, masked_password) = cast(PasswordOnDisk, visitor.to_disk(value))
    assert masked_password == "******"


@patch("cmk.gui.watolib.password_visitor.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    "value",
    [
        RawDiskData({"el": ("cmk_postprocessed", "explicit_password", ("", "some_password"))}),
        RawFrontendData({"el": ("explicit_password", "", "some_password", False)}),
    ],
)
def test_nested_password_gets_masked(  # type: ignore[misc]
    patch_pwstore: None,  # noqa: ARG001
    request_context: None,  # noqa: ARG001
    value: IncomingData,
) -> None:
    spec = Dictionary(elements={"el": DictElement(parameter_form=Password())})
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=True))
    dict_result = cast(dict[str, PasswordOnDisk], visitor.to_disk(value))
    _, _, (_, masked_password) = dict_result["el"]
    assert masked_password == "******"


@patch("cmk.gui.watolib.password_visitor.passwordstore_choices", return_value=[])
@pytest.mark.parametrize(
    ["old", "new"],
    [
        pytest.param(
            RawDiskData(("password", "secret-password")),
            (
                "cmk_postprocessed",
                "explicit_password",
                (
                    ANY,
                    "secret-password",
                ),
            ),
            id="migrate explicit password",
        ),
        pytest.param(
            RawDiskData(("store", "password_1")),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="migrate stored password",
        ),
        pytest.param(
            RawDiskData(("explicit_password", "uuid067408f0-d390-4dcc-ae3c-966f278ace7d", "abc")),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("uuid067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="old 3-tuple explicit password",
        ),
        pytest.param(
            RawDiskData(("stored_password", "password_1", "")),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="old 3-tuple stored password",
        ),
        pytest.param(
            RawDiskData(
                (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
                )
            ),
            (
                "cmk_postprocessed",
                "explicit_password",
                ("uuid067408f0-d390-4dcc-ae3c-966f278ace7d", "abc"),
            ),
            id="already migrated explicit password",
        ),
        pytest.param(
            RawDiskData(("cmk_postprocessed", "stored_password", ("password_1", ""))),
            ("cmk_postprocessed", "stored_password", ("password_1", "")),
            id="already migrated stored password",
        ),
    ],
)
def test_password_migrates_password_on_disk(  # type: ignore[misc]
    patch_pwstore: None,  # noqa: ARG001
    request_context: None,  # noqa: ARG001
    old: IncomingData,
    new: PasswordOnDisk,
) -> None:
    disk_visitor = get_visitor(
        Password(migrate=migrate_to_password),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    disk_visitor_password = disk_visitor.to_disk(old)
    assert new == disk_visitor_password


_GENERATED_ID = "uuid067408f0-d390-4dcc-ae3c-966f278ace7d"


@pytest.mark.parametrize(
    "password_id, kept",
    [
        pytest.param(_GENERATED_ID, True, id="generated ID"),
        pytest.param("admin_secret", False, id="ID of a stored password"),
        pytest.param("my_own_id", False, id="ID of the user's choice"),
        pytest.param("", False, id="no ID"),
    ],
)
@pytest.mark.usefixtures("request_context", "mock_password_file_regeneration")
def test_explicit_password_keeps_only_generated_ids_of_no_stored_password(
    password_id: str, kept: bool
) -> None:
    PasswordStore().save(
        {
            "admin_secret": PasswordConfig(
                title="", comment="", docu_url="", password="s3crit", owned_by=None, shared_with=[]
            )
        },
        pprint_value=False,
    )
    visitor = get_visitor(Password(), VisitorOptions(migrate_values=True, mask_values=False))

    _, _, (saved_id, saved_password) = cast(
        PasswordOnDisk,
        visitor.to_disk(RawFrontendData(("explicit_password", password_id, "my_secret", False))),
    )

    assert saved_password == "my_secret"
    assert (saved_id == password_id) is kept
    assert is_ad_hoc_password_id(saved_id)
