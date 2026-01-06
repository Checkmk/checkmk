#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.ccc.version import Edition, edition

from cmk.utils import paths

from cmk.gui.form_specs.private.dictionary_extended import DictGroupExtended, DictionaryExtended
from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.http import request
from cmk.gui.valuespec.definitions import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import NotificationParameter

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Integer,
    MultilineText,
    MultipleChoice,
    MultipleChoiceElement,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import EmailAddress as ValidateEmailAddress
from cmk.shared_typing.vue_formspec_components import DictionaryGroupLayout

from ._helpers import _get_url_prefix_setting


class NotificationParameterMail(NotificationParameter):
    @property
    def ident(self) -> str:
        return "mail"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return recompose(self._form_spec()).valuespec  # type: ignore[return-value]  # expects Valuespec[Any]

    def _form_spec(self) -> DictionaryExtended:
        # TODO register CSE specific version
        return DictionaryExtended(
            title=Title("HTML Email parameters"),
            elements=self._parameter_elements(is_cse=edition(paths.omd_root) == Edition.CSE),
            ignored_elements=("no_floating_graphs",),
        )

    def _parameter_elements(self, is_cse: bool) -> dict[str, DictElement[Any]]:
        return {
            **self._settings_elements(is_cse),
            **_header_elements(is_cse),
            **_content_elements(),
            **_testing_elements(),
            **_bulk_elements(),
        }

    def _settings_elements(self, is_cse: bool) -> dict[str, DictElement[Any]]:
        return self._url_prefix_setting(is_cse)

    def _url_prefix_setting(self, is_cse: bool) -> dict[str, DictElement[Any]]:
        return {
            "url_prefix": _get_url_prefix_setting(
                is_cse,
                default_value="automatic_https" if request.is_ssl_request else "automatic_http",
                group_title="Settings",
            )
        }


class NotificationParameterASCIIMail(NotificationParameter):
    @property
    def ident(self) -> str:
        return "asciimail"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return recompose(self._form_spec()).valuespec  # type: ignore[return-value]

    def _form_spec(self) -> DictionaryExtended:
        return DictionaryExtended(
            title=Title("ASCII Email parameters"),
            elements=_elements_ascii(is_cse=edition(paths.omd_root) == Edition.CSE),
        )


def _elements_ascii(is_cse: bool) -> Mapping[str, DictElement[Any]]:
    elements = {
        "from": _from_address_element(is_cse),
        "reply_to": _reply_to(),
        "host_subject": _host_subject(),
        "service_subject": _service_subject(),
        "common_body": DictElement(
            parameter_form=MultilineText(
                title=Title("Body head for both host and service notifications"),
                prefill=DefaultValue(
                    """\
Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
"""
                ),
                macro_support=True,
            ),
        ),
        "host_body": DictElement(
            parameter_form=MultilineText(
                title=Title("Body tail for host notifications"),
                prefill=DefaultValue(
                    """\
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""
                ),
                macro_support=True,
            ),
        ),
        "service_body": DictElement(
            parameter_form=MultilineText(
                title=Title("Body tail for service notifications"),
                prefill=DefaultValue(
                    """\
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""
                ),
                macro_support=True,
            ),
        ),
        "bulk_sort_order": _bulk_sort_order(),
        "disable_multiplexing": _disable_multiplexing(is_cse),
    }

    return elements


def _header_elements(is_cse: bool) -> dict[str, DictElement[Any]]:
    return {
        "from": _from_address_element(is_cse),
        "reply_to": _reply_to(),
        "disable_multiplexing": _disable_multiplexing(is_cse),
        "host_subject": _host_subject(),
        "service_subject": _service_subject(),
    }


def _content_elements() -> dict[str, DictElement[Any]]:
    return {
        "insert_html_section": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=MultilineText(
                title=Title("Custom HTML section (e.g. title, description…)"),
                prefill=DefaultValue("<HTMLTAG>CONTENT</HTMLTAG>"),
                macro_support=True,
                help_text=Help("Only simple tags like 'h1', 'b' or 'i' are allowed."),
            ),
        ),
        # TODO should be old ListChoice style
        "elements": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=MultipleChoice(
                title=Title("Additional details"),
                elements=[
                    MultipleChoiceElement(
                        name="omdsite",
                        title=Title("Site ID"),
                    ),
                    MultipleChoiceElement(
                        name="address",
                        title=Title("IP Address of Hosts"),
                    ),
                    MultipleChoiceElement(
                        name="abstime",
                        title=Title("Absolute time of alert"),
                    ),
                    MultipleChoiceElement(
                        name="reltime",
                        title=Title("Relative time of alert"),
                    ),
                    MultipleChoiceElement(
                        name="longoutput",
                        title=Title("Plugin output"),
                    ),
                    MultipleChoiceElement(
                        name="ack_author",
                        title=Title("Acknowledgment author"),
                    ),
                    MultipleChoiceElement(
                        name="ack_comment",
                        title=Title("Acknowledgement comment"),
                    ),
                    MultipleChoiceElement(
                        name="notification_author",
                        title=Title("Notification author"),
                    ),
                    MultipleChoiceElement(
                        name="notification_comment",
                        title=Title("Notification comment"),
                    ),
                    MultipleChoiceElement(
                        name="perfdata",
                        title=Title("Metrics"),
                    ),
                    MultipleChoiceElement(
                        name="graph",
                        title=Title("Time series graph"),
                    ),
                    MultipleChoiceElement(
                        name="notesurl",
                        title=Title("Custom host/service notes URL"),
                    ),
                    MultipleChoiceElement(
                        name="context",
                        title=Title("Complete variable list (for testing)"),
                    ),
                ],
                prefill=DefaultValue(["abstime", "longoutput", "graph"]),
            ),
        ),
        "contact_groups": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=FixedValue(
                title=Title("Show contact groups"),
                label=Label(""),
                value=True,
            ),
        ),
        "svc_labels": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=FixedValue(
                title=Title("Show service labels"),
                label=Label(""),
                value=True,
            ),
        ),
        "host_labels": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=FixedValue(
                title=Title("Show host labels"),
                label=Label(""),
                value=True,
            ),
        ),
        "host_tags": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=FixedValue(
                title=Title("Show host tags"),
                label=Label(""),
                value=True,
            ),
        ),
        "graphs_per_notification": DictElement(
            group=DictGroupExtended(
                title=Title("Email body/content"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=Integer(
                title=Title("Number of graphs per notification (default: 5)"),
                label=Label("Show up to"),
                unit_symbol="graphs",
                prefill=DefaultValue(5),
                help_text=Help(
                    "Sets a limit for the number of "
                    "graphs that are displayed in "
                    "a notification."
                ),
            ),
        ),
    }


def _bulk_elements() -> dict[str, DictElement[Any]]:
    return {
        "bulk_sort_order": _bulk_sort_order(),
        "notifications_with_graphs": DictElement(
            group=DictGroupExtended(
                title=Title("Bulk notifications"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=Integer(
                title=Title(
                    "Limit number of events with graphs per bulk notification (default: 5)"
                ),
                label=Label("Show graphs for the first"),
                unit_symbol="notifications",
                prefill=DefaultValue(5),
                help_text=Help(
                    "Sets a limit for the number of notifications in a bulk for "
                    "which graphs are displayed. If you do not use bulk "
                    "notifications this option is ignored. Note that each graph "
                    "increases the size of the mail and takes time to render on "
                    "the monitoring server. Therefore, large bulks may exceed "
                    "the maximum size for attachements or the plug-in may run "
                    "into a timeout so that a failed notification is produced."
                ),
            ),
        ),
    }


def _testing_elements() -> dict[str, DictElement[Any]]:
    return {
        "notification_rule": DictElement(
            group=DictGroupExtended(
                title=Title("Troubleshooting/testing settings"),
                layout=DictionaryGroupLayout.vertical,
            ),
            parameter_form=FixedValue(
                title=Title("Show notification rule that triggered the notification"),
                label=Label(""),
                value=True,
            ),
        ),
    }


def _from_address_element(is_cse: bool) -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title("Email header"),
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=Dictionary(
            title=Title('Custom sender ("From")'),
            elements={
                "address": DictElement(
                    parameter_form=String(
                        title=Title("Email address"),
                        custom_validate=[ValidateEmailAddress()],
                    ),
                ),
                "display_name": DictElement(
                    parameter_form=String(
                        title=Title("Display name"),
                    ),
                ),
            },
        ),
        render_only=is_cse,
    )


def _reply_to() -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title("Email header"),
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=Dictionary(
            title=Title('Custom recipient of "Reply to"'),
            elements={
                "address": DictElement(
                    parameter_form=String(
                        title=Title("Email address"),
                        custom_validate=[ValidateEmailAddress()],
                    ),
                ),
                "display_name": DictElement(
                    parameter_form=String(
                        title=Title("Display name"),
                    ),
                ),
            },
        ),
    )


def _disable_multiplexing(is_cse: bool) -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title("Email header"),
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=FixedValue(
            title=Title("Hide other recipients: Send individual notifications to each recipient"),
            help_text=Help(
                "Per default only "
                "one notification is generated "
                "for all recipients. Therefore, "
                "all recipients can see who was "
                "notified and reply to all other "
                "recipients."
            ),
            value=True,
            label=Label(
                "A separate notification is "
                "sent to every recipient. Recipients "
                "cannot see which other recipients "
                "were notified."
            ),
        ),
        render_only=is_cse,
    )


def _host_subject() -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title("Email header"),
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=String(
            title=Title("Subject line for host notifications"),
            help_text=Help(
                "Here you are allowed to use "
                "all macros that are defined in "
                "the notification context."
            ),
            prefill=DefaultValue("Checkmk: $HOSTNAME$ - $EVENT_TXT$"),
            field_size=FieldSize.LARGE,
            macro_support=True,
        ),
    )


def _service_subject() -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title("Email header"),
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=String(
            title=Title("Subject line for service notifications"),
            help_text=Help(
                "Here you are allowed to use "
                "all macros that are defined in "
                "the notification context."
            ),
            prefill=DefaultValue("Checkmk: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$"),
            field_size=FieldSize.LARGE,
            macro_support=True,
        ),
    )


def _bulk_sort_order() -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title("Bulk notifications"),
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=SingleChoice(
            title=Title("Notification sort order for bulk notifications"),
            elements=[
                SingleChoiceElement(name="oldest_first", title=Title("Oldest first")),
                SingleChoiceElement(name="newest_first", title=Title("Newest first")),
            ],
            help_text=Help(
                "With this option you can "
                "specify, whether the oldest "
                "(default) or the newest "
                "notification should get shown "
                "at the top of the notification "
                "mail."
            ),
            prefill=DefaultValue("newest_first"),
        ),
    )
