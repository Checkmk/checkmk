#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The address of a statistics widget's link whose filters take the values of all objects a
part stands for. Only a click queries them, so a refresh of the widget never has to."""

from collections.abc import Iterator, Mapping
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Json, NonNegativeInt, ValidationError

from cmk.ccc.user import UserId
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.pages import PageContext
from cmk.gui.top_heading import requested_drill_up
from cmk.gui.type_defs import AnnotatedUserId, FilterHTTPVariables, FilterName, VisualContext
from cmk.gui.views.drilldown_filters import Dropped
from cmk.shared_typing.drill_up_button import DrillUpButton

from .api import EffectiveLink
from .api.compute_stats import stats_link_properties, StatsLinkPart
from .api.model.link_properties import DeferredFilter, DroppedFilter, EncodedFilter, FilterResult
from .api.model.widget_content import content_from_internal
from .store import get_permitted_dashboards_by_owners
from .type_defs import DashletConfig
from .view_drilldown import target_url, TimeRangeVariables

PAGE_STATS_LINK = "dashboard_stats_link"


class _StatsLinkRequest(BaseModel):
    dashboard_name: str
    dashboard_owner: Literal[""] | AnnotatedUserId
    widget_id: str
    part: StatsLinkPart
    link_index: NonNegativeInt
    context: Annotated[VisualContext, Json]
    time_range: TimeRangeVariables | None

    @classmethod
    def from_request(cls, request: Request) -> Self:
        try:
            return cls.model_validate(
                {
                    "dashboard_name": request.get_str_input("dashboard_name"),
                    "dashboard_owner": request.get_str_input("dashboard_owner"),
                    "widget_id": request.get_str_input("widget_id"),
                    "part": request.get_str_input("part"),
                    "link_index": request.get_str_input("link_index"),
                    "context": request.get_str_input("context", "{}"),
                    "time_range": _time_range_input(request),
                }
            )
        except ValidationError as e:
            raise MKUserError("request", _("Invalid request parameters.")) from e

    def widget_config(self) -> DashletConfig:
        owner = UserId.builtin() if self.dashboard_owner == "" else self.dashboard_owner
        try:
            dashboard = get_permitted_dashboards_by_owners()[self.dashboard_name][owner]
        except KeyError:
            raise MKUserError(
                "dashboard_name",
                _(
                    "The dashboard '%(name)s' does not exist or you do not have permission to "
                    "view it."
                )
                % {"name": self.dashboard_name},
            ) from None
        if (config := dashboard["widgets"].get(self.widget_id)) is None:
            raise MKUserError(
                "widget_id",
                _("The dashboard has no widget '%(widget)s'.") % {"widget": self.widget_id},
            )
        return config


def page_stats_link(ctx: PageContext) -> None:
    """Redirect to the target of a click on a part or the total of a statistics widget."""
    params = _StatsLinkRequest.from_request(ctx.request)
    link, properties = stats_link_properties(
        content_from_internal(params.widget_config()),
        params.context,
        ctx.user_permissions,
        params.part,
        params.link_index,
    )
    raise HTTPRedirect(
        _link_url(
            link,
            properties,
            params.context,
            params.time_range,
            requested_drill_up(ctx.request),
        )
    )


def _time_range_input(request: Request) -> dict[str, str | None] | None:
    from_, to = request.get_str_input("from"), request.get_str_input("to")
    return None if from_ is None and to is None else {"from_": from_, "to": to}


def _link_url(
    link: EffectiveLink,
    properties: Mapping[FilterName, FilterResult],
    context: VisualContext,
    time_range: TimeRangeVariables | None,
    drilled_from: DrillUpButton | None,
) -> str:
    filters: dict[FilterName, FilterHTTPVariables] = {
        **(context if link.include_context else {}),
        **{
            filter_name: result.variables
            for filter_name, result in properties.items()
            if isinstance(result, EncodedFilter)
        },
    }
    return target_url(
        link.location,
        filters,
        show_filter_form=link.show_filter_form,
        drilled_from=drilled_from,
        time_range=time_range if link.include_time_range else None,
        dropped=list(_dropped(properties, filters)),
    )


def _dropped(
    properties: Mapping[FilterName, FilterResult], filters: Mapping[FilterName, object]
) -> Iterator[Dropped]:
    for filter_name, result in properties.items():
        match result:
            case EncodedFilter():
                # A key the clicked element lacks drops alone, while the filter carries the others.
                for key in _keys(result.missing_keys):
                    yield Dropped(filter_name, "no_such_key", key)
            case _ if filter_name in filters:
                # A filter the context carries in place of the clicked element's value travels.
                continue
            case DeferredFilter():
                yield Dropped(filter_name, "no_value")
            case DroppedFilter():
                if not (keys := _keys(result.missing_keys)):
                    yield Dropped(filter_name, result.reason)
                for key in keys:
                    yield Dropped(filter_name, result.reason, key)


def _keys(missing_keys: list[str] | ApiOmitted) -> list[str]:
    return missing_keys if isinstance(missing_keys, list) else []
