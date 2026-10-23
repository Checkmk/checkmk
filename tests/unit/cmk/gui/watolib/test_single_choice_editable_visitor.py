#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.form_specs.unstable import FolderChoiceEditable, SingleChoiceEditable
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.configuration_entity import ConfigEntityType


@pytest.mark.usefixtures("with_admin_login")
def test_single_choice_editable() -> None:
    spec = SingleChoiceEditable(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="mail",
    )

    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))

    assert visitor.validate(RawFrontendData("foo")) == []
    assert visitor.to_vue(RawFrontendData("foo"))[1] == "foo"


@pytest.mark.usefixtures("with_admin_login")
def test_single_choice_editable_none_complains_nicely() -> None:
    spec = SingleChoiceEditable(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="mail",
    )
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))

    validation = visitor.validate(RawFrontendData(None))

    assert len(validation) == 1
    assert validation[0].message.startswith("Please choose parameters")


@pytest.mark.usefixtures("request_context")
def test_single_choice_editable_rejects_the_folder_entity_type() -> None:
    """Folder choices carry their own choices; the entity listing has no tree to list folders"""
    spec = SingleChoiceEditable(
        entity_type=ConfigEntityType.folder,
        entity_type_specifier="all",
    )
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))

    with pytest.raises(MKGeneralException, match="FolderChoiceEditable"):
        visitor.to_vue(RawFrontendData("sub"))


@pytest.mark.usefixtures("request_context")
def test_folder_choice_editable_lists_the_handed_in_folders() -> None:
    """The folder choice shows the choices of its caller's tree, not those of a global tree"""
    spec = FolderChoiceEditable(folder_choices=lambda: [("", "Main"), ("sub", "Main / Sub")])

    vue_spec, value = get_visitor(
        spec, VisitorOptions(migrate_values=True, mask_values=False)
    ).to_vue(RawFrontendData("sub"))

    assert isinstance(vue_spec, shared_type_defs.SingleChoiceEditable)
    assert [(element.name, element.title) for element in vue_spec.elements] == [
        ("", "Main"),
        ("sub", "Main / Sub"),
    ]
    assert value == "sub"
