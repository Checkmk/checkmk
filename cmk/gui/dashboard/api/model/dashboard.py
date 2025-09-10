#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
from abc import ABC, abstractmethod
from collections.abc import Container, Iterable, Sequence
from typing import Annotated, Literal, override, Self

from pydantic import AfterValidator, Discriminator

from cmk.ccc.user import UserId
from cmk.gui.dashboard import DashboardConfig
from cmk.gui.dashboard.page_edit_dashboard import dashboard_info_handler
from cmk.gui.dashboard.type_defs import DashboardRelativeGridLayoutSpec
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    GroupConverter,
    RegistryConverter,
    SiteIdConverter,
)
from cmk.gui.openapi.restful_objects.validators import RequestDataValidator
from cmk.gui.type_defs import (
    AnnotatedUserId,
    DashboardEmbeddedViewSpec,
    FilterName,
    Icon,
    VisualContext,
)
from cmk.gui.views.icon.registry import all_icons
from cmk.gui.watolib.main_menu import main_module_topic_registry

from .type_defs import AnnotatedInfoName
from .widget import BaseWidgetRequest, RelativeGridWidgetRequest, RelativeGridWidgetResponse
from .widget_content.view import EmbeddedViewContent


@api_model
class DashboardTitle:
    text: str = api_field(description="The title of the dashboard.")
    render: bool = api_field(description="Displays the title when viewing the dashboard.")
    include_context: bool = api_field(description="Include the context in the title.")


type IconName = Annotated[str, AfterValidator(RegistryConverter(lambda x: all_icons()).validate)]


@api_model
class DashboardIcon:
    name: IconName = api_field(description="The icon name.")
    emblem: IconName | ApiOmitted = api_field(
        description="Additional icon name, that will be displayed as a smaller emblem.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, icon: Icon | None) -> Self | ApiOmitted:
        if icon is None:
            return ApiOmitted()
        if isinstance(icon, str):
            return cls(name=icon, emblem=ApiOmitted())
        return cls(name=icon["icon"], emblem=icon.get("emblem") or ApiOmitted())

    @classmethod
    def to_internal(cls, icon: Self | ApiOmitted) -> Icon | None:
        if isinstance(icon, ApiOmitted):
            return None
        if isinstance(icon.emblem, ApiOmitted):
            return icon.name
        return {"icon": icon.name, "emblem": icon.emblem}


def _validate_topic(value: str) -> str:
    # NOTE: `other` is not in the registry, but is the default value for the topic
    if value != "other" and value not in main_module_topic_registry:
        raise ValueError(
            f"Invalid topic, valid options are: {', '.join(main_module_topic_registry)}"
        )

    return value


@api_model
class DashboardMenuSettings:
    topic: Annotated[str, AfterValidator(_validate_topic)] = api_field(
        description="Which section in the `Monitor` menu this dashboard is displayed under."
    )
    sort_index: int = api_field(description="Order of the dashboard within the topic.")
    icon: DashboardIcon | ApiOmitted = api_field(
        description="Which icon to display, if the main menu icons are enabled.",
        default_factory=ApiOmitted,
    )
    is_show_more: bool = api_field(
        description="If set, this dashboard will be displayed in the `Show more` section of the `Monitor` menu."
    )
    search_terms: list[str] = api_field(
        description="A list of search terms that can be used to find this dashboard in the `Monitor` menu."
    )


@api_model
class DashboardShareWithAllUsers:
    share_type: Literal["with_all_users"] = api_field(
        serialization_alias="type", description="Share the dashboard with all other users."
    )


@api_model
class DashboardShareWithContactGroups:
    share_type: Literal["with_contact_groups"] = api_field(
        serialization_alias="type",
        description="Share the dashboard with users of these contact groups.",
    )
    contact_groups: list[Annotated[str, AfterValidator(GroupConverter("contact").exists)]]


@api_model
class DashboardShareWithSites:
    share_type: Literal["with_sites"] = api_field(
        serialization_alias="type",
        description="Share the dashboard with users of these sites. The sites need to activate changes for this to take effect.",
    )
    sites: list[Annotated[str, AfterValidator(SiteIdConverter.should_exist)]]


# NOTE: mypy can't handle a union of Literal and Annotated, unless they are split up like this
type _ShareOptions = Annotated[
    DashboardShareWithAllUsers | DashboardShareWithContactGroups | DashboardShareWithSites,
    Discriminator("share_type"),
]
type DashboardShare = Literal["no"] | _ShareOptions


@api_model
class DashboardVisibility:
    hide_in_monitor_menu: bool = api_field(description="Hide this dashboard in the `Monitor` menu.")
    hide_in_drop_down_menus: bool = api_field(description="Hide this dashboard in drop down menus.")
    share: DashboardShare = api_field(description="Make this dashboard available to other users.")

    @staticmethod
    def share_from_internal(
        public: bool | tuple[Literal["contact_groups", "sites"], Sequence[str]],
    ) -> DashboardShare:
        if isinstance(public, tuple):
            share_type, values = public
            if share_type == "contact_groups":
                return DashboardShareWithContactGroups(
                    share_type="with_contact_groups",
                    contact_groups=list(values),
                )
            if share_type == "sites":
                return DashboardShareWithSites(
                    share_type="with_sites",
                    sites=list(values),
                )
            raise ValueError(f"Invalid share type: {share_type}")

        return DashboardShareWithAllUsers(share_type="with_all_users") if public else "no"

    def share_to_internal(self) -> bool | tuple[Literal["contact_groups", "sites"], Sequence[str]]:
        if isinstance(self.share, DashboardShareWithAllUsers):
            return True
        if isinstance(self.share, DashboardShareWithContactGroups):
            return "contact_groups", self.share.contact_groups
        if isinstance(self.share, DashboardShareWithSites):
            return "sites", self.share.sites
        return False


@api_model
class DashboardRelativeGridLayout:
    type: Literal["relative_grid"] = api_field(
        description="The dashboard is in a relative grid layout.",
    )

    def to_internal(self) -> DashboardRelativeGridLayoutSpec:
        return DashboardRelativeGridLayoutSpec(type=self.type)


@api_model
class DashboardFilterContext:
    restricted_to_single: list[AnnotatedInfoName] = api_field(
        description=(
            "A list of single infos that this dashboard is restricted to. "
            "This means that the dashboard must be filtered to exactly one item for each info name."
        )
    )
    filters: VisualContext = api_field(
        description="Active filters in the format filter_id -> (variable -> value)"
    )
    mandatory_context_filters: list[FilterName] = api_field(
        description="Filters that are required to use this dashboard."
    )


@api_model
class DashboardGeneralSettings:
    title: DashboardTitle = api_field(
        description="Title settings.", example={"text": "My Dashboard", "render": True}
    )
    description: str | ApiOmitted = api_field(
        description="Description of the dashboard.",
        default_factory=ApiOmitted,
        example="This dashboard shows ...",
    )
    menu: DashboardMenuSettings = api_field(description="Settings relating to the main menu.")
    visibility: DashboardVisibility = api_field(
        description="Settings relating to the dashboards visibility."
    )

    @classmethod
    def from_internal(cls, dashboard: DashboardConfig) -> Self:
        api_general_settings = cls(
            title=DashboardTitle(
                text=str(dashboard["title"]),
                render=dashboard["show_title"],
                include_context=dashboard["add_context_to_title"],
            ),
            menu=DashboardMenuSettings(
                topic=dashboard["topic"],
                sort_index=dashboard["sort_index"],
                icon=DashboardIcon.from_internal(dashboard.get("icon")),
                is_show_more=dashboard["is_show_more"],
                search_terms=list(dashboard["main_menu_search_terms"]),
            ),
            visibility=DashboardVisibility(
                hide_in_monitor_menu=dashboard.get("hidden", False),
                hide_in_drop_down_menus=dashboard.get("hidebutton", False),
                share=DashboardVisibility.share_from_internal(dashboard["public"]),
            ),
        )
        if "description" in dashboard:
            api_general_settings.description = str(dashboard["description"])
        return api_general_settings


@api_model
class DashboardFilterContextResponse(DashboardFilterContext):
    uses_infos: list[AnnotatedInfoName] = api_field(
        description=(
            "A list of info names that this dashboard uses. "
            "This is used to determine the available filters."
        )
    )

    @classmethod
    def from_internal(cls, dashboard: DashboardConfig) -> Self:
        return cls(
            restricted_to_single=list(dashboard["single_infos"]),
            filters=dashboard["context"],
            uses_infos=list(dashboard_info_handler(dashboard)),
            mandatory_context_filters=dashboard["mandatory_context_filters"],
        )


@api_model
class _BaseDashboard:
    general_settings: DashboardGeneralSettings = api_field(
        description="General settings for the dashboard.",
    )
    filter_context: DashboardFilterContext = api_field(
        description="Filter context for the dashboard.",
    )


@api_model
class BaseDashboardRequest(_BaseDashboard, ABC):
    @abstractmethod
    def _iter_widgets(self) -> Iterable[BaseWidgetRequest]:
        """Iterate over all widgets that are part of this dashboard."""
        pass

    @abstractmethod
    def to_internal(
        self, owner: UserId, dashboard_id: str, embedded_views: dict[str, DashboardEmbeddedViewSpec]
    ) -> DashboardConfig:
        """Convert the API model to the internal representation."""
        pass

    def _get_used_embedded_views(self) -> set[str]:
        """Return a set of all embedded view IDs that are used in this dashboard."""
        return {
            widget.content.embedded_id
            for widget in self._iter_widgets()
            if isinstance(widget.content, EmbeddedViewContent)
        }

    def _to_internal_without_layout(
        self, owner: UserId, dashboard_id: str, embedded_views: dict[str, DashboardEmbeddedViewSpec]
    ) -> DashboardConfig:
        used_embedded_views = self._get_used_embedded_views()
        embedded_views = {k: v for k, v in embedded_views.items() if k in used_embedded_views}

        return DashboardConfig(
            owner=owner,
            name=dashboard_id,
            context=self.filter_context.filters,
            single_infos=self.filter_context.restricted_to_single,
            add_context_to_title=self.general_settings.title.include_context,
            title=self.general_settings.title.text,
            description=(
                ""
                if isinstance(self.general_settings.description, ApiOmitted)
                else self.general_settings.description
            ),
            topic=self.general_settings.menu.topic,
            sort_index=self.general_settings.menu.sort_index,
            is_show_more=self.general_settings.menu.is_show_more,
            icon=DashboardIcon.to_internal(self.general_settings.menu.icon),
            hidden=self.general_settings.visibility.hide_in_monitor_menu,
            hidebutton=self.general_settings.visibility.hide_in_drop_down_menus,
            public=self.general_settings.visibility.share_to_internal(),
            packaged=False,
            link_from={},
            main_menu_search_terms=self.general_settings.menu.search_terms,
            mtime=int(dt.datetime.now(tz=dt.UTC).timestamp()),
            show_title=self.general_settings.title.render,
            mandatory_context_filters=self.filter_context.mandatory_context_filters,
            dashlets=[widget.to_internal() for widget in self._iter_widgets()],
            embedded_views=embedded_views,
        )


@api_model
class BaseDashboardResponse(_BaseDashboard):
    # these fields should only be present in responses
    owner: AnnotatedUserId = api_field(description="The owner of the dashboard.", example="admin")
    last_modified_at: dt.datetime = api_field(
        description="The last modification time of the dashboard."
    )
    filter_context: DashboardFilterContextResponse = api_field(
        description="Filter context for the dashboard."
    )


@api_model
class BaseRelativeGridDashboardRequest(BaseDashboardRequest):
    layout: DashboardRelativeGridLayout = api_field(description="The layout the dashboard uses.")
    widgets: dict[str, RelativeGridWidgetRequest] = api_field(
        description="All widgets that are part of this dashboard.",
    )

    def validate(self, context: ApiContext, *, embedded_views: Container[str]) -> None:
        """Run additional validation that depends on the API context (or rather the config)."""
        errors = [
            error
            for widget_id, widget in self.widgets.items()
            for error in widget.iter_validation_errors(
                ("body", "widgets", widget_id),
                context=context,
                embedded_views=embedded_views,
            )
        ]
        if errors:
            raise RequestDataValidator.format_error_details(errors)

    @override
    def _iter_widgets(self) -> Iterable[BaseWidgetRequest]:
        return self.widgets.values()

    @override
    def to_internal(
        self, owner: UserId, dashboard_id: str, embedded_views: dict[str, DashboardEmbeddedViewSpec]
    ) -> DashboardConfig:
        config = self._to_internal_without_layout(owner, dashboard_id, embedded_views)
        config["layout"] = self.layout.to_internal()
        return config


@api_model
class RelativeGridDashboardResponse(BaseDashboardResponse):
    layout: DashboardRelativeGridLayout = api_field(description="The layout the dashboard uses.")
    widgets: dict[str, RelativeGridWidgetResponse] = api_field(
        description="All widgets that are part of this dashboard.",
    )

    @classmethod
    def from_internal(cls, dashboard: DashboardConfig) -> Self:
        api_dashboard = cls(
            owner=dashboard["owner"],
            last_modified_at=dt.datetime.fromtimestamp(dashboard["mtime"], tz=dt.UTC),
            general_settings=DashboardGeneralSettings.from_internal(dashboard),
            filter_context=DashboardFilterContextResponse.from_internal(dashboard),
            widgets={
                f"{dashboard['name']}-{idx}": RelativeGridWidgetResponse.from_internal(dashlet)
                for idx, dashlet in enumerate(dashboard["dashlets"])
            },
            layout=DashboardRelativeGridLayout(type="relative_grid"),
        )
        return api_dashboard
