#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.ms_teams_constants import (
    ms_teams_tmpl_host_details,
    ms_teams_tmpl_host_summary,
    ms_teams_tmpl_host_title,
    ms_teams_tmpl_svc_details,
    ms_teams_tmpl_svc_summary,
    ms_teams_tmpl_svc_title,
)

from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.watolib.password_store import passwordstore_choices_without_user

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    migrate_to_proxy,
    MultilineText,
    Proxy,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange

from ._helpers import (
    _get_url_prefix_setting,
    notification_macro_help_fs,
)


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Microsoft Teams parameters"),
        elements={
            "webhook_url": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Webhook URL"),
                    prefill=DefaultValue("webhook_url"),
                    help_text=Help(
                        "Create a workflow 'Post to a channel when a "
                        "webhook request is received' for a channel in MS "
                        "Teams and use the generated webook URL.<br><br>"
                        "This URL can also be collected from the Password "
                        "Store from Checkmk."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="webhook_url",
                            title=Title("Explicit"),
                            parameter_form=String(
                                custom_validate=[
                                    LengthInRange(
                                        min_value=1,
                                        error_msg=Message("Please enter a valid Webhook URL"),
                                    )
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="store",
                            title=Title("From password store"),
                            parameter_form=SingleChoiceExtended(
                                no_elements_text=Message(
                                    "There are no passwords defined for this selection yet."
                                ),
                                elements=[
                                    SingleChoiceElementExtended(
                                        title=Title("%s") % title, name=ident
                                    )
                                    for ident, title in passwordstore_choices_without_user()
                                    if ident is not None
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            "proxy_url": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
            "url_prefix": _get_url_prefix_setting(),
            "host_title": DictElement(
                parameter_form=String(
                    title=Title("Title for host notifications"),
                    help_text=notification_macro_help_fs(),
                    prefill=DefaultValue(ms_teams_tmpl_host_title()),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "service_title": DictElement(
                parameter_form=String(
                    title=Title("Title for service notifications"),
                    help_text=notification_macro_help_fs(),
                    prefill=DefaultValue(ms_teams_tmpl_svc_title()),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "host_summary": DictElement(
                parameter_form=String(
                    title=Title("Summary for host notifications"),
                    help_text=notification_macro_help_fs(),
                    prefill=DefaultValue(ms_teams_tmpl_host_summary()),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "service_summary": DictElement(
                parameter_form=String(
                    title=Title("Summary for service notifications"),
                    help_text=notification_macro_help_fs(),
                    prefill=DefaultValue(ms_teams_tmpl_svc_summary()),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "host_details": DictElement(
                parameter_form=MultilineText(
                    title=Title("Details for host notifications"),
                    help_text=notification_macro_help_fs(),
                    monospaced=True,
                    prefill=DefaultValue(ms_teams_tmpl_host_details()),
                ),
            ),
            "service_details": DictElement(
                parameter_form=MultilineText(
                    title=Title("Details for service notifications"),
                    help_text=notification_macro_help_fs(),
                    monospaced=True,
                    prefill=DefaultValue(ms_teams_tmpl_svc_details()),
                ),
            ),
            "affected_host_groups": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Show affected host groups"),
                    label=Label("Show affected host groups"),
                    help_text=Help("Show affected host groups in the created message."),
                ),
            ),
        },
    )
