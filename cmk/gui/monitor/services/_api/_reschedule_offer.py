#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What rescheduling a single service means, decided per row.

The legacy views never offered a plain "reschedule me" on every row: a service whose result is a
byproduct of the agent-based ``Check_MK`` check has nothing of its own to run, so the legacy icon
(``cmk.gui.views.icon.builtin._render_reschedule_icon``) redirects it to the host's ``Check_MK``
service, and refuses outright where no check can be forced at all. This module is that decision,
for the Vue view; the frontend only renders what comes out of it.
"""

from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.painter.v0.helpers import render_cache_info

from .._models import CheckType, Service

# A service whose check command names it a byproduct of the agent-based check. The ``Check_MK``
# service itself runs ``check-mk`` and so is not one of them - it reschedules itself.
_AGENT_BASED_PREFIX = "check_mk-"

# The service that actually fetches the agent data the byproducts are parsed from.
_AGENT_SERVICE = "Check_MK"


@api_model
class ServiceRescheduleOffer:
    label: str = api_field(
        description="Label for the reschedule action", example="Reschedule check"
    )
    tooltip: str = api_field(
        description="Tooltip for the reschedule action; explains the refusal when blocked",
        example="Reschedule check",
    )
    icon_name: str = api_field(description="Icon to render for the action", example="reload")
    target: str | ApiOmitted = api_field(
        description=(
            "The service a reschedule acts on, which is not always the service shown: a byproduct "
            "of the agent-based check reschedules the host's 'Check_MK' service instead. Omitted "
            "when this service cannot be rescheduled at all, in which case the action is shown but "
            "not clickable."
        ),
        example="Check_MK",
        default_factory=ApiOmitted,
    )


def _blocked(reason: str) -> ServiceRescheduleOffer:
    return ServiceRescheduleOffer(
        label=_("Reschedule check"),
        tooltip=reason,
        icon_name="cannot-reschedule",
    )


def build_reschedule_offer(service: Service) -> ServiceRescheduleOffer | None:
    """What the row's reschedule action does, or ``None`` where it is not shown at all."""
    if not user.may("action.reschedule"):
        return None

    if service.check_type is CheckType.SHADOW:
        return _blocked(
            _("This service is monitored by a remote site and cannot be rescheduled here.")
        )

    if service.cached_at:
        cache_info = render_cache_info(
            "service",
            {
                "service_cached_at": service.cached_at,
                "service_cache_interval": service.cache_interval,
            },
        )
        return _blocked(
            _("This service is based on cached agent data and cannot be rescheduled.")
            + " "
            + cache_info
        )

    if service.check_command.startswith(_AGENT_BASED_PREFIX):
        return ServiceRescheduleOffer(
            label=_("Reschedule 'Check_MK' service"),
            tooltip=_("Reschedule 'Check_MK' service"),
            icon_name="reload-cmk",
            target=_AGENT_SERVICE,
        )

    if service.active_checks_enabled:
        return ServiceRescheduleOffer(
            label=_("Reschedule check"),
            tooltip=_("Reschedule check"),
            icon_name="reload",
            target=service.name,
        )

    return _blocked(
        _("Active checks are disabled for this service, so it cannot be rescheduled.")
        if service.check_type is CheckType.ACTIVE
        else _("This service is checked passively and cannot be rescheduled.")
    )
