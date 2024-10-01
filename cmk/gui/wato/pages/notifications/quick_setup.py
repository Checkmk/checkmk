#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData, QuickSetupId
from cmk.gui.quick_setup.v0_unstable.widgets import Widget
from cmk.gui.watolib.mode import mode_url


def triggering_events() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Triggering events"),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Specify host/services"),
    )


def filter_for_hosts_and_services() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Filter for hosts/services"),
        sub_title=_(
            "Apply filters to specify which hosts and services are affected by this "
            "notification rule."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Notification method (plug-in)"),
    )


def notification_method() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Notification method (plug-in)"),
        sub_title=_("What should be send out?"),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Recipient"),
    )


def recipient() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Recipient"),
        sub_title=_("Who should receive the notification?"),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Sending conditions"),
    )


def sending_conditions() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Sending conditions"),
        sub_title=_(
            "Specify when and how notifications are sent based on frequency, timing, and "
            "content criteria."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: General properties"),
    )


def general_properties() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("General properties"),
        sub_title=_(
            "Review your notification rule before applying it. They will take effect right "
            "away without 'Activate changes'."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Saving"),
    )


def save_action(all_stages_form_data: ParsedFormData) -> str:
    return mode_url("test_notifications")


def register(quick_setup_registry: QuickSetupRegistry) -> None:
    quick_setup_registry.register(quick_setup_notifications)


quick_setup_notifications = QuickSetup(
    title=_("Notification rule"),
    id=QuickSetupId("notification_rule"),
    stages=[
        triggering_events,
        filter_for_hosts_and_services,
        notification_method,
        recipient,
        sending_conditions,
        general_properties,
    ],
    save_action=save_action,
    button_complete_label=_("Apply & test notification rule"),
)
