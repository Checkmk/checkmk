#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.ccc.i18n import _

from cmk.gui.form_specs.generators.folder import create_full_path_folder_choice
from cmk.gui.form_specs.private import Catalog, Topic, TopicElement
from cmk.gui.form_specs.private.validators import not_empty
from cmk.gui.form_specs.vue.form_spec_visitor import process_validation_messages
from cmk.gui.form_specs.vue.visitors._registry import get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin, VisitorOptions
from cmk.gui.watolib.hosts_and_folders import find_available_folder_name, Folder, folder_tree

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import String
from cmk.rulesets.v1.form_specs.validators import ValidationError

INTERNAL_TRANSFORM_ERROR = _("FormSpec and internal data structure mismatch")


def folder_is_writable(name: str) -> None:
    if not folder_tree().all_folders()[name].permissions.may("write"):
        raise ValidationError(Message("You do not have write permission for this folder."))


def get_folder_slidein_schema() -> Catalog:
    return Catalog(
        elements={
            "general": Topic(
                title=Title("Basic settings"),
                elements={
                    "title": TopicElement(
                        parameter_form=String(
                            title=Title("Title"),
                            custom_validate=[not_empty()],
                        ),
                        required=True,
                    ),
                    "parent_folder": TopicElement(
                        parameter_form=create_full_path_folder_choice(
                            title=Title("Parent folder"),
                            help_text=Help("Select the parent folder"),
                            custom_validate=[folder_is_writable],
                        ),
                        required=True,
                    ),
                },
            )
        }
    )


@dataclass(frozen=True, kw_only=True)
class FolderDescription:
    title: str
    path: str


@dataclass(frozen=True, kw_only=True)
class _ParsedFS:
    title: str
    parent_folder: str


def _parse_fs(data: object) -> _ParsedFS:
    if not isinstance(data, dict):
        raise ValueError(INTERNAL_TRANSFORM_ERROR)

    try:
        general = data["general"]
        if not isinstance(general, dict):
            raise ValueError(INTERNAL_TRANSFORM_ERROR)

        return _ParsedFS(
            title=general["title"],
            parent_folder=general["parent_folder"],
        )
    except KeyError as exc:
        raise ValueError(INTERNAL_TRANSFORM_ERROR) from exc


def _append_full_parent_title(title: str, parent_folder: Folder | None) -> str:
    if parent_folder is None or parent_folder.name() == "":
        return title
    return f"{_append_full_parent_title(parent_folder.title(), parent_folder.parent())}/{title}"


def save_folder_from_slidein_schema(data: object, *, pprint_value: bool) -> FolderDescription:
    """Save a folder from data returned from folder slide in.

    Raises:
        FormSpecValidationError: if the data does not match the form spec
    """
    form_spec = get_folder_slidein_schema()
    visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.FRONTEND))

    validation_errors = visitor.validate(data)
    process_validation_messages(validation_errors)

    disk_data = visitor.to_disk(data)
    parsed_data = _parse_fs(disk_data)

    parent_folder = folder_tree().all_folders()[parsed_data.parent_folder]
    name = find_available_folder_name(parsed_data.title, parent_folder)
    folder = parent_folder.create_subfolder(
        name=name, title=parsed_data.title, attributes={}, pprint_value=pprint_value
    )
    full_title = _append_full_parent_title(folder.title(), parent_folder)

    return FolderDescription(title=full_title, path=folder.path())
