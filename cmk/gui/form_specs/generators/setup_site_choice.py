#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import TypeVar

from cmk.ccc.site import omd_site

from cmk.gui import site_config
from cmk.gui.config import active_config
from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.logged_in import user as global_user
from cmk.gui.user_sites import activation_sites, site_choices

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue, InvalidElementValidator

T = TypeVar("T")


def _compute_default_prefill() -> DefaultValue[str]:
    if site_config.is_wato_slave_site(active_config.sites):
        # Placeholder for "central site". This is only relevant when using Setup on a remote site
        # and a host / folder has no site set.
        return DefaultValue("")

    if not (
        authorized_site_ids := list(
            global_user.authorized_sites(unfiltered_sites=active_config.sites).keys()
        )
    ):
        return DefaultValue("")

    site_id = omd_site()
    if site_id in authorized_site_ids:
        return DefaultValue(site_id)
    return DefaultValue(authorized_site_ids[0])


def _compute_site_choices() -> Sequence[SingleChoiceElementExtended[str]]:
    return [
        SingleChoiceElementExtended(
            name=choice[0],
            title=Title(choice[1]),  # pylint: disable=localization-of-non-literal-string
        )
        for choice in site_choices(activation_sites())
    ]


def create_setup_site_choice(
    title: Title = Title("Site"),
    help_text: Help | None = None,
    label: Label | None = None,
    elements: Sequence[SingleChoiceElementExtended[str]] | None = None,
    prefill: DefaultValue[str] | None = None,
    invalid_element_validation: InvalidElementValidator | None = None,
) -> SingleChoiceExtended[str]:
    if elements is None:
        elements = _compute_site_choices()
    if prefill is None:
        prefill = _compute_default_prefill()

    return SingleChoiceExtended(
        title=title,
        help_text=help_text,
        label=label,
        elements=elements,
        invalid_element_validation=invalid_element_validation,
        prefill=prefill,
    )
