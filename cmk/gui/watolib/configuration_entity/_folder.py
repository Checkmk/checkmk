#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.form_specs.generators.folder import create_full_path_folder_choice
from cmk.gui.form_specs.private.catalog import Catalog, Topic, TopicElement
from cmk.gui.form_specs.private.validators import not_empty

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import String


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
                        ),
                        required=True,
                    ),
                },
            )
        }
    )
