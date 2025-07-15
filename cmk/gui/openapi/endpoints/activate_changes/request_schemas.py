#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.utils import param_description
from cmk.gui.watolib.activate_changes import activate_changes_start


class ActivateChanges(BaseSchema):
    redirect = fields.Boolean(
        description="After starting the activation, redirect immediately to the 'Wait for completion' endpoint.",
        required=False,
        load_default=False,
        example=False,
    )
    sites = fields.List(
        gui_fields.SiteField(presence="ignore"),
        description=(
            "The names of the sites on which the configuration shall be activated."
            " An empty list means all sites which have pending changes."
        ),
        required=False,
        load_default=list,
        example=["production"],
    )
    force_foreign_changes = fields.Boolean(
        description=param_description(activate_changes_start.__doc__, "force_foreign_changes"),
        required=False,
        load_default=False,
        example=False,
    )
