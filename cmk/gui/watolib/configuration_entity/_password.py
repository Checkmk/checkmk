#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Literal

from cmk.ccc.i18n import _
from cmk.gui.form_specs import (
    get_visitor,
    process_validation_messages,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable import Catalog, CommentTextArea, Topic, TopicElement
from cmk.gui.form_specs.unstable.legacy_converter import SimplePassword
from cmk.gui.form_specs.unstable.validators import not_empty
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.watolib.passwords import (
    load_passwords,
    password_exists,
    save_password,
    sorted_contact_group_choices,
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.utils.password_store._pwstore import Password

INTERNAL_TRANSFORM_ERROR = _("FormSpec and internal data structure mismatch")


def _password_id_exists_validator(password_id: str) -> None:
    if password_exists(password_id):
        raise ValidationError(Message("This ID is already in use. Please choose another one."))


def get_password_slidein_schema(user: LoggedInUser) -> Catalog:
    if user.may("wato.edit_all_passwords"):
        admin_element = [
            CascadingSingleChoiceElement(
                name="admins",
                title=Title("Administrators"),
                parameter_form=FixedValue(
                    value=None,
                    label=Label(
                        'Administrators (having the permission "Write access to all passwords")'
                    ),
                ),
            )
        ]
    else:
        admin_element = []

    return Catalog(
        elements={
            "general_props": Topic(
                title=Title("General properties"),
                elements={
                    "id": TopicElement(
                        parameter_form=String(
                            title=Title("Unique ID"),
                            custom_validate=[not_empty(), _password_id_exists_validator],
                        ),
                        required=True,
                    ),
                    "title": TopicElement(
                        parameter_form=String(
                            title=Title("Title"),
                            custom_validate=[not_empty()],
                        ),
                        required=True,
                    ),
                    "comment": TopicElement(
                        parameter_form=CommentTextArea(
                            title=Title("Comment"),
                        ),
                        required=True,
                    ),
                    "docu_url": TopicElement(
                        parameter_form=String(
                            title=Title("Documentation URL"),
                        ),
                        required=True,
                    ),
                },
            ),
            "password_props": Topic(
                title=Title("Password properties"),
                elements={
                    "password": TopicElement(
                        parameter_form=SimplePassword(
                            title=Title("Password"),
                        ),
                        required=True,
                    ),
                    "owned_by": TopicElement(
                        parameter_form=CascadingSingleChoice(
                            title=Title("Editable by"),
                            prefill=DefaultValue("admins")
                            if admin_element
                            else DefaultValue("contact_group"),
                            elements=admin_element
                            + [
                                CascadingSingleChoiceElement(
                                    name="contact_group",
                                    title=Title("Members of the contact group:"),
                                    parameter_form=SingleChoice(
                                        elements=[
                                            SingleChoiceElement(
                                                name=name,
                                                title=Title(  # astrein: disable=localization-checker
                                                    title
                                                ),
                                            )
                                            for name, title in sorted_contact_group_choices(
                                                only_own=True
                                            )
                                        ],
                                        no_elements_text=Message(
                                            "You need to be member of at least one contact group to be able to "
                                            "create a password."
                                        ),
                                    ),
                                ),
                            ],
                        ),
                        required=True,
                    ),
                    "share_with": TopicElement(
                        parameter_form=MultipleChoice(
                            title=Title("Share with"),
                            help_text=Help(
                                "By default only the members of the owner contact group are permitted "
                                "to use a a configured password. It is possible to share a password with "
                                "other groups of users to make them able to use a password in checks."
                            ),
                            elements=[
                                MultipleChoiceElement(
                                    name=name,
                                    title=Title(title),  # astrein: disable=localization-checker
                                )
                                for name, title in sorted_contact_group_choices(only_own=False)
                            ],
                        ),
                        required=True,
                    ),
                },
            ),
        }
    )


@dataclass(frozen=True, kw_only=True)
class PasswordDescription:
    id: str
    title: str


@dataclass(frozen=True, kw_only=True)
class _ParsedGeneralProps:
    id: str
    title: str
    comment: str
    docu_url: str


@dataclass(frozen=True, kw_only=True)
class _ParsedPasswordProps:
    password: str
    owned_by: tuple[Literal["admins"], None] | tuple[Literal["contact_group"], str]
    share_with: list[str]


@dataclass(frozen=True, kw_only=True)
class _ParsedPassword:
    general_props: _ParsedGeneralProps
    password_props: _ParsedPasswordProps


def _parse_fs(data: object) -> _ParsedPassword:
    if not isinstance(data, dict):
        raise ValueError(INTERNAL_TRANSFORM_ERROR)

    try:
        general_props = data["general_props"]
        if not isinstance(general_props, dict):
            raise ValueError(INTERNAL_TRANSFORM_ERROR)

        password_props = data["password_props"]
        if not isinstance(password_props, dict):
            raise ValueError(INTERNAL_TRANSFORM_ERROR)

        return _ParsedPassword(
            general_props=_ParsedGeneralProps(
                id=general_props["id"],
                title=general_props["title"],
                comment=general_props["comment"],
                docu_url=general_props["docu_url"],
            ),
            password_props=_ParsedPasswordProps(
                password=password_props["password"],
                owned_by=password_props["owned_by"],
                share_with=password_props["share_with"],
            ),
        )
    except KeyError as exc:
        raise ValueError(INTERNAL_TRANSFORM_ERROR) from exc


def save_password_from_slidein_schema(
    data: RawFrontendData, *, user: LoggedInUser, pprint_value: bool, use_git: bool
) -> PasswordDescription:
    """Save a password from data returned from password slide in.

    Raises:
        FormSpecValidationError: if the data does not match the form spec
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.passwords")

    form_spec = get_password_slidein_schema(user)
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))

    validation_errors = visitor.validate(data)
    process_validation_messages(validation_errors)

    disk_data = visitor.to_disk(data)
    parsed_data = _parse_fs(disk_data)

    # should already be validated by the form spec, but make sure here
    if password_exists(parsed_data.general_props.id):
        raise ValueError(_("This ID is already in use. Please choose another one."))

    owned_by = None
    match parsed_data.password_props.owned_by:
        case ("admins", None):
            owned_by = None
        case ("contact_group", str(contact_group_name)):
            owned_by = contact_group_name
        case _other:
            raise ValueError(INTERNAL_TRANSFORM_ERROR)

    save_password(
        ident=parsed_data.general_props.id,
        details=Password(
            title=parsed_data.general_props.title,
            comment=parsed_data.general_props.comment,
            docu_url=parsed_data.general_props.docu_url,
            password=parsed_data.password_props.password,
            owned_by=owned_by,
            shared_with=parsed_data.password_props.share_with,
        ),
        new_password=True,
        user_id=user.id,
        pprint_value=pprint_value,
        use_git=use_git,
    )
    return PasswordDescription(
        id=parsed_data.general_props.id, title=parsed_data.general_props.title
    )


def list_passwords(user: LoggedInUser) -> list[PasswordDescription]:
    """List passwords visible to the given user."""
    user.need_permission("wato.passwords")
    return [
        PasswordDescription(id=ident, title=pw["title"]) for ident, pw in load_passwords().items()
    ]
