#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import dataclasses
from collections.abc import Generator
from typing import Annotated, cast, get_args, Literal, override, Self

from pydantic import BaseModel, Json, model_validator, ValidationError

from cmk.ccc.user import UserId
from cmk.gui.dashboard import DashboardConfig, dashlet_registry, get_all_dashboards
from cmk.gui.dashboard.page_show_shared_dashboard import SharedDashboardPageComponents
from cmk.gui.dashboard.store import get_permitted_dashboards_by_owners, save_all_dashboards
from cmk.gui.dashboard.token_util import (
    DashboardTokenAuthenticatedPage,
    get_dashboard_widget_by_id,
    get_shared_dashboard_url,
    impersonate_dashboard_token_issuer,
    ImpersonatedDashboardTokenIssuer,
    InvalidWidgetError,
)
from cmk.gui.dashboard.type_defs import EmbeddedViewDashletConfig, LinkedViewDashletConfig
from cmk.gui.data_source import data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import Page, PageContext, PageResult
from cmk.gui.painter_options import PainterOptions
from cmk.gui.permissions import permission_registry
from cmk.gui.token_auth import AuthToken, DashboardToken
from cmk.gui.type_defs import (
    AnnotatedUserId,
    DashboardEmbeddedViewSpec,
    SingleInfos,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.view_renderer import GUIViewRenderer
from cmk.gui.views.page_edit_view import create_view_from_valuespec, render_view_config
from cmk.gui.views.page_show_view import get_limit, get_user_sorters, process_view
from cmk.gui.views.store import get_permitted_views, get_view_by_name
from cmk.gui.visuals import get_only_sites_from_context
from cmk.gui.visuals.info import visual_info_registry

__all__ = ["ViewWidgetIFramePage", "ViewWidgetIFrameTokenPage", "ViewWidgetEditPage"]


class EmbeddedViewSpecManager:
    @classmethod
    def get_embedded_view_spec(
        cls, dashboard: DashboardConfig, embedded_id: str, view_name: str
    ) -> ViewSpec:
        embedded_views = dashboard.get("embedded_views", {})
        if embedded_id not in embedded_views:
            raise MKUserError(
                "embedded_id",
                _("The dashboard '%s' does not contain an embedded view with the ID '%s'.")
                % (dashboard["name"], embedded_id),
            )

        return cls.embedded_to_normal_view_spec(
            embedded_views[embedded_id],
            dashboard["owner"],
            name=view_name,
        )

    @classmethod
    def normal_to_embedded_view_spec(cls, spec: ViewSpec) -> DashboardEmbeddedViewSpec:
        embedded = DashboardEmbeddedViewSpec(
            single_infos=spec["single_infos"],
            datasource=spec["datasource"],
            layout=spec["layout"],
            group_painters=spec["group_painters"],
            painters=spec["painters"],
            browser_reload=spec["browser_reload"],
            num_columns=spec["num_columns"],
            column_headers=spec["column_headers"],
            sorters=spec["sorters"],
        )
        cls._copy_optionals(source=spec, target=embedded)
        return embedded

    @classmethod
    def embedded_to_normal_view_spec(
        cls, spec: DashboardEmbeddedViewSpec, dashboard_owner: UserId, name: str
    ) -> ViewSpec:
        view_spec = ViewSpec(
            owner=dashboard_owner,
            name=name,
            single_infos=spec["single_infos"],
            datasource=spec["datasource"],
            layout=spec["layout"],
            group_painters=spec["group_painters"],
            painters=spec["painters"],
            sorters=spec["sorters"],
            browser_reload=spec["browser_reload"],
            num_columns=spec["num_columns"],
            column_headers=spec["column_headers"],
            context={},
            add_context_to_title=False,
            title="",
            description="",
            topic="",
            sort_index=0,
            is_show_more=False,
            icon=None,
            hidden=False,
            hidebutton=False,
            public=False,
            packaged=False,
            link_from={},
            main_menu_search_terms=[],
        )
        cls._copy_optionals(source=spec, target=view_spec)
        return view_spec

    @staticmethod
    def _copy_optionals(
        source: ViewSpec | DashboardEmbeddedViewSpec, target: ViewSpec | DashboardEmbeddedViewSpec
    ) -> None:
        if add_headers := source.get("add_headers"):
            target["add_headers"] = add_headers
        if mobile := source.get("mobile"):
            target["mobile"] = mobile
        if mustsearch := source.get("mustsearch"):
            target["mustsearch"] = mustsearch
        if force_checkboxes := source.get("force_checkboxes"):
            target["force_checkboxes"] = force_checkboxes
        if play_sounds := source.get("play_sounds"):
            target["play_sounds"] = play_sounds
        if inventory_join_macros := source.get("inventory_join_macros"):
            target["inventory_join_macros"] = inventory_join_macros


class ViewWidgetIFramePageHelper:
    @classmethod
    def render_iframe_content(
        cls,
        widget_name: str,
        view_spec: ViewSpec,
        row_limit: int | None,
        context: VisualContext,
        user_permissions: UserPermissions,
        *,
        is_reload: bool,
        is_debug: bool,
    ) -> None:
        view_spec = cls._prepare_view_spec(view_spec)
        view = View(
            widget_name,
            view_spec,
            context,
            user_permissions=user_permissions,
        )
        view.row_limit = row_limit
        view.only_sites = get_only_sites_from_context(context)
        view.user_sorters = get_user_sorters(view.spec["sorters"], view.row_cells)
        with cls._wrapper_context(is_reload):
            process_view(
                GUIViewRenderer(
                    view,
                    show_buttons=False,
                    page_menu_dropdowns_callback=lambda x, y, z: None,
                ),
                user_permissions=user_permissions,
                debug=is_debug,
            )

    @staticmethod
    def setup_display_and_painter_options(
        request: Request, widget_name: str, is_reload: bool
    ) -> None:
        """Setup display options and painter options for the view widget iframe page."""
        if not is_reload:
            view_display_options = "HRSIXLW"

            request.set_var("display_options", view_display_options)
            request.set_var("_display_options", view_display_options)

        # Need to be loaded before processing the painter_options below.
        # TODO: Make this dependency explicit
        display_options.load_from_html(request, html)

        painter_options = PainterOptions.get_instance()
        painter_options.load(widget_name)

    @staticmethod
    def setup_filled_in(request: Request) -> None:
        """The `filled_in` query parameter needs to be set in order for rows to be fetched,
        this method sets a default value."""
        if request.var("filled_in") is None:
            request.set_var("filled_in", "filter")

    @staticmethod
    def _prepare_view_spec(view_spec: ViewSpec) -> ViewSpec:
        """Override some view widget specific options."""
        view_spec = view_spec.copy()
        view_spec["user_sortable"] = False
        return view_spec

    @classmethod
    def _wrapper_context(cls, is_reload: bool) -> contextlib.AbstractContextManager[None]:
        if not is_reload:
            return cls._content_wrapper()

        return contextlib.nullcontext()

    @staticmethod
    @contextlib.contextmanager
    def _content_wrapper() -> Generator[None]:
        html.add_body_css_class("view")
        html.add_body_css_class("dashlet")
        html.open_div(id_="dashlet_content_wrapper")
        try:
            yield None
        finally:
            html.close_div()
            html.javascript('cmk.utils.add_simplebar_scrollbar("dashlet_content_wrapper");')


class _ViewWidgetIFrameAuthTokenRequestParameters(BaseModel):
    widget_id: str
    display_options: str | None

    @classmethod
    def from_request(cls, request: Request) -> Self:
        try:
            return cls.model_validate(
                dict(
                    widget_id=request.get_str_input("widget_id"),
                    display_options=request.get_str_input(
                        "display_options", request.get_str_input("_display_options")
                    ),
                )
            )
        except ValidationError as e:
            raise MKUserError("request", _("Invalid request parameters.")) from e

    def is_reload(self) -> bool:
        return self.display_options is not None


class _ViewWidgetIFrameRequestParameters(_ViewWidgetIFrameAuthTokenRequestParameters):
    dashboard_name: str
    dashboard_owner: Literal[""] | AnnotatedUserId
    view_name: str | None
    embedded_id: str | None
    raw_context: Annotated[VisualContext, Json]
    limit: Literal["soft", "hard", "none"]
    raw_debug: str | None

    @override
    @classmethod
    def from_request(cls, request: Request) -> Self:
        try:
            return cls.model_validate(
                dict(
                    dashboard_name=request.get_str_input("dashboard_name"),
                    dashboard_owner=request.get_str_input("dashboard_owner"),
                    widget_id=request.get_str_input("widget_id"),
                    view_name=request.get_str_input("view_name"),
                    embedded_id=request.get_str_input("embedded_id"),
                    raw_context=request.get_str_input("context", "{}"),
                    limit=request.get_str_input("limit", "soft"),
                    display_options=request.get_str_input(
                        "display_options", request.get_str_input("_display_options")
                    ),
                    raw_debug=request.get_str_input("debug"),
                )
            )
        except ValidationError as e:
            raise MKUserError("request", _("Invalid request parameters.")) from e

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.embedded_id and self.view_name:
            raise MKUserError(
                "view_name",
                _("Cannot specify both 'view_name' and 'embedded_id' parameters."),
            )
        return self

    def is_debug(self) -> bool:
        return self.raw_debug == "1"

    def unique_widget_name(self) -> str:
        return f"{self.dashboard_owner}_{self.dashboard_name}_{self.widget_id}"

    def load_view_spec(self) -> ViewSpec:
        """Load the requested view spec, either embedded in the dashboard or a normal view."""
        if self.embedded_id:
            return self._get_embedded_view_spec(self.embedded_id)

        return self._get_linked_view_spec()

    def _get_linked_view_spec(self) -> ViewSpec:
        if not self.view_name:
            raise MKUserError("view_name", _("No view name provided."))

        view_spec = get_permitted_views().get(self.view_name)
        if not view_spec:
            raise MKUserError("name", _("No view defined with the name '%s'.") % self.view_name)

        return view_spec

    def _get_embedded_view_spec(self, embedded_id: str) -> ViewSpec:
        if not self.dashboard_name:
            raise MKUserError("dashboard", _("No dashboard name provided."))

        dashboards = get_permitted_dashboards_by_owners()
        owner = UserId.builtin() if self.dashboard_owner == "" else self.dashboard_owner
        try:
            dashboard = dashboards[self.dashboard_name][owner]
        except KeyError:
            raise MKUserError(
                "dashboard",
                _("The dashboard '%s' does not exist or you do not have permission to view it.")
                % self.dashboard_name,
            ) from None

        return EmbeddedViewSpecManager.get_embedded_view_spec(
            dashboard,
            embedded_id,
            f"{self.dashboard_name}_{embedded_id}",
        )

    def get_context(self) -> VisualContext:
        return {
            filter_name: filter_values
            for filter_name, filter_values in self.raw_context.items()
            # only include filters which have at least one set value
            if {
                var: value
                for var, value in filter_values.items()
                # These are the filters request variables. Keep set values
                # For the TriStateFilters unset == ignore == "-1"
                # all other cases unset is an empty string
                if (var.startswith("is_") and value != "-1")  # TriState filters except ignore
                or (not var.startswith("is_") and value)  # Rest of filters with some value
            }
        }


class ViewWidgetIFramePage(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        """Render a single view for use in an iframe.

        This needs to support two modes:
            1. Render an existing linked view, identified by its name
            2. Render a view that's embedded in the dashboard config, identified by its internal ID
        """
        parameters = _ViewWidgetIFrameRequestParameters.from_request(ctx.request)
        ViewWidgetIFramePageHelper.setup_display_and_painter_options(
            ctx.request, parameters.unique_widget_name(), parameters.is_reload()
        )
        try:
            view_spec = parameters.load_view_spec()
        except MKUserError as e:
            # a linked view used by a widget can be (intentionally) deleted,
            # so we need to handle this gracefully so that the rest of the dashboard still works
            html.body_start()
            html.write_html(html.render_error(str(e)))
            return

        ViewWidgetIFramePageHelper.setup_filled_in(ctx.request)

        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        row_limit = get_limit(
            request_limit_mode=parameters.limit,
            soft_query_limit=ctx.config.soft_query_limit,
            may_ignore_soft_limit=user.may("general.ignore_soft_limit"),
            hard_query_limit=ctx.config.hard_query_limit,
            may_ignore_hard_limit=user.may("general.ignore_hard_limit"),
        )
        ViewWidgetIFramePageHelper.render_iframe_content(
            parameters.unique_widget_name(),
            view_spec,
            row_limit,
            parameters.get_context(),
            user_permissions,
            is_reload=parameters.is_reload(),
            is_debug=parameters.is_debug(),
        )


class ViewWidgetIFrameTokenPage(DashboardTokenAuthenticatedPage):
    def _get_view_spec_by_widget_id(
        self,
        issuer: ImpersonatedDashboardTokenIssuer,
        token_details: DashboardToken,
        dashboard: DashboardConfig,
        widget_id: str,
        unique_widget_name: str,
    ) -> ViewSpec:
        widget_config = get_dashboard_widget_by_id(dashboard, widget_id)
        widget_type = dashlet_registry[widget_config["type"]]
        widget = widget_type(widget_config, dashboard.get("context"))
        if widget_config["type"] == "linked_view":
            view_spec = self._get_linked_view_spec(
                token_details, widget_id, cast(LinkedViewDashletConfig, widget_config), issuer
            )
        elif widget_config["type"] == "embedded_view":
            view_spec = self._get_embedded_view_spec(
                dashboard, cast(EmbeddedViewDashletConfig, widget_config), unique_widget_name
            )
        else:
            raise InvalidWidgetError()

        view_spec = view_spec.copy()
        view_spec["context"] = widget.context
        return view_spec

    @staticmethod
    def _get_linked_view_spec(
        token_details: DashboardToken,
        widget_id: str,
        widget: LinkedViewDashletConfig,
        issuer: ImpersonatedDashboardTokenIssuer,
    ) -> ViewSpec:
        if widget_id not in token_details.view_owners:
            # this means that the person sharing the dashboard wasn't permitted to see this view
            raise MKAuthException(_("The token owner did not have access to this view."))

        expected_view_owner = token_details.view_owners[widget_id]

        view_spec = issuer.load_linked_view(widget["name"])
        if view_spec["owner"] != expected_view_owner or (
            view_spec["owner"] != UserId.builtin()  # modified_at is only set for custom views
            and "modified_at" in view_spec  # modified_at is only set on views updated since 2.5
            and view_spec["modified_at"] > token_details.synced_at.isoformat()
        ):
            # disable the token here, because the view owner does not match the expected owner
            # or the view has been modified since the token was last updated
            raise InvalidWidgetError(disable_token=True)

        return view_spec

    @staticmethod
    def _get_embedded_view_spec(
        dashboard: DashboardConfig, widget: EmbeddedViewDashletConfig, unique_widget_name: str
    ) -> ViewSpec:
        embedded_id = widget["name"]
        if embedded_id not in dashboard.get("embedded_views", {}):
            # disable the token here, because we know the widget ID is valid for an embedded view,
            # but the dashboard does not contain an embedded view with the expected ID
            raise InvalidWidgetError(disable_token=True)

        return EmbeddedViewSpecManager.embedded_to_normal_view_spec(
            dashboard["embedded_views"][embedded_id],
            dashboard["owner"],
            name=unique_widget_name,
        )

    @override
    def _get(self, token: AuthToken, token_details: DashboardToken, ctx: PageContext) -> None:
        parameters = _ViewWidgetIFrameAuthTokenRequestParameters.from_request(ctx.request)
        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)

        with impersonate_dashboard_token_issuer(
            token.issuer, token_details, user_permissions
        ) as issuer:
            dashboard = issuer.load_dashboard()
            unique_widget_name = f"{dashboard['name']}_{parameters.widget_id}"
            view_spec = self._get_view_spec_by_widget_id(
                issuer, token_details, dashboard, parameters.widget_id, unique_widget_name
            )

        ViewWidgetIFramePageHelper.setup_display_and_painter_options(
            ctx.request, unique_widget_name, parameters.is_reload()
        )
        ViewWidgetIFramePageHelper.setup_filled_in(ctx.request)

        ViewWidgetIFramePageHelper.render_iframe_content(
            unique_widget_name,
            view_spec,
            row_limit=ctx.config.soft_query_limit,
            context={},
            user_permissions=user_permissions,
            is_reload=parameters.is_reload(),
            is_debug=False,
        )

    @override
    def _redirect_to_shared_dashboard_page(self, token: AuthToken) -> PageResult:
        # Since we're in an iframe we cannot just return a redirect response.
        # We also shouldn't just update `window.top`, since we expect shared dashboards to be used
        # within iframes as well.
        # Instead of assuming the depth level we're in, the better approach is to walk up the stack
        # until we find the right page (shared_dashboard.py), falling back to the current window.
        search_name = f"{SharedDashboardPageComponents.page_name}.py"
        target_url = get_shared_dashboard_url(token.token_id)
        # we cannot use &, as that will currently be escaped by the html.javascript function
        # thankfully we can convert it using de morgans law: A && B -> !(!A || !B)
        html.javascript(
            f"""
            let win = window;
            let found = false;
            try {{
                while (!(!win.parent || win.parent === win)) {{
                    if (!(!win.parent.location || !win.parent.location.href.includes({search_name!r}))) {{
                        win.parent.location.href = {target_url!r};
                        found = true;
                        break;
                    }}
                    win = win.parent;
                }}
            }} catch (e) {{
                // Cross-origin access error, stop walking up
            }}
            if (!found) {{
                window.location.href = {target_url!r};
            }}
            """
        )
        return None


class ViewWidgetEditPage(Page):
    type Mode = Literal["create", "copy", "edit"]

    @dataclasses.dataclass(kw_only=True, slots=True)
    class ConfigurationErrorMessage:
        type: Literal["cmk:view:configuration-error"] = "cmk:view:configuration-error"
        message: str

    @dataclasses.dataclass(kw_only=True, slots=True)
    class ValidationErrorMessage:
        type: Literal["cmk:view:validation-error"] = "cmk:view:validation-error"

    @dataclasses.dataclass(kw_only=True, slots=True)
    class SaveCompletedMessage:
        type: Literal["cmk:view:save-completed"] = "cmk:view:save-completed"
        datasource: str
        single_infos: SingleInfos

    @override
    def page(self, ctx: PageContext) -> None:
        """Render the view editor for embedded views in dashboards.

        This reuses the existing view editor, but should only show the view specific fields.
        The page is expected to be used in an iframe, so it should not render any header.

        The page supports three modes:
            - create: Create a new embedded view from scratch. Requires the datasource and
                      single_infos query args.
            - copy: Create a new embedded view by copying an existing view. Requires the view_name
                    query arg.
            - edit: Edit an existing embedded view.

        In addition, the following query args are always used:
            - mode: The mode of the editor, one of "create", "copy", "edit".
            - dashboard: The name of the dashboard the view is embedded in.
            - owner: The owner of the dashboard. Must match the logged-in user, unless the user
                     has the `general.edit_foreign_dashboards` permission and the mode is "edit".
            - embedded_id: The internal ID of the embedded view in the dashboard. Must be generated
                           on the client side even for new views.

        The page communicates with the parent window via the JavaScript postMessage function.
        It sends the following messages:
            - Configuration error: Sent when the page cannot be rendered due to missing or invalid
                                   query args. The message contains a human-readable error message.
            - Validation error: Sent when the user tries to save the view, but the validation fails.
                                The user can then fix the error and try again. Used to re-enable the
                                save button in the parent window.
            - Save completed: Sent when the user successfully saves the view. The parent window can
                              then close the editor and proceed to the next step.

        This page is expected to contain a hidden save button with the name "_save", which will be
        interacted with via JavaScript from the parent window.
        """
        try:
            user.need_permission("general.edit_dashboards")
            dashboard_name = ctx.request.get_ascii_input_mandatory("dashboard")
            embedded_id = ctx.request.get_ascii_input_mandatory("embedded_id")
            mode = self._get_mode(ctx.request)
            owner = self._get_owner(ctx.request, mode)

            dashboard = self._load_dashboard(owner, dashboard_name)
            view_spec = self._get_view_spec(ctx.request, dashboard, embedded_id, mode)
        except (MKUserError, MKAuthException) as e:
            # we can't render the view editor with invalid input, notify the parent window
            self._post_message(self.ConfigurationErrorMessage(message=str(e)))
            return  # nothing the user can do, stop rendering the rest

        error = None
        if ctx.request.var("_save"):
            try:
                self._save(dashboard, embedded_id, view_spec)
            except MKUserError as e:
                error = e
            else:
                # on save, we only want to notify the parent that we're done
                # this is handled on the dashboard view workflow side
                # because of the copy mode, we need to send back the data source and single infos
                self._post_message(
                    self.SaveCompletedMessage(
                        datasource=view_spec["datasource"], single_infos=view_spec["single_infos"]
                    )
                )
                return  # we're done, stop rendering the rest

        html.body_start()  # include CSS to render the view editor properly
        # remove the 10px padding that body.main adds
        html.open_div(style="margin-left: -10px;")
        if error:
            html.show_error(str(error))
            # we need to let the frontend know that the save failed
            self._post_message(self.ValidationErrorMessage())

        with html.form_context("widget_view", method="POST"):
            # we use the hidden "_save" button via the parent windows javascript

            html.hidden_field("dashboard", dashboard_name)
            html.hidden_field("embedded_id", embedded_id)
            html.hidden_field("datasource", view_spec["datasource"])
            html.hidden_field("single_infos", ",".join(view_spec["single_infos"]))
            html.hidden_field("mode", "edit" if mode == "edit" else "create")  # copy -> create
            html.hidden_field("owner", str(owner))

            render_view_config(view_spec, general_properties=True)

        html.close_div()
        html.body_end()

    @staticmethod
    def _post_message(
        message: ConfigurationErrorMessage | ValidationErrorMessage | SaveCompletedMessage,
    ) -> None:
        serialized = dataclasses.asdict(message)
        html.javascript(f"window.parent.postMessage({serialized!r})")

    @staticmethod
    def _save(dashboard: DashboardConfig, embedded_id: str, view_spec: ViewSpec) -> None:
        # first arg is just used for the datasource (so it can't be overwritten)
        view_spec = create_view_from_valuespec(old_view=view_spec, view=view_spec)
        embedded = EmbeddedViewSpecManager.normal_to_embedded_view_spec(view_spec)
        dashboard.setdefault("embedded_views", {})[embedded_id] = embedded
        save_all_dashboards(dashboard["owner"])
        # we don't do the remote site sync here, as this is done when the dashboard is saved
        # we accept that this might drift apart for now

    @staticmethod
    def _get_mode(request: Request) -> Mode:
        mode = request.get_ascii_input_mandatory("mode")
        if mode not in get_args(ViewWidgetEditPage.Mode.__value__):
            raise MKUserError("mode", _("Invalid mode '%s'.") % mode)
        return cast(ViewWidgetEditPage.Mode, mode)

    @staticmethod
    def _get_owner(request: Request, mode: Mode) -> UserId:
        owner_id = request.get_validated_type_input_mandatory(UserId, "owner", user.id)
        if owner_id != user.id:
            if mode == "edit":
                # we're editing views that are saved inside the dashboard config
                if not user.may("general.edit_foreign_dashboards"):
                    raise MKAuthException(
                        _("You are not allowed to edit foreign %s.") % "dashboards"
                    )
            else:  # create/copy mode
                raise MKAuthException(_("Mismatching owner in `%s` mode.") % mode)
        return owner_id

    @staticmethod
    def _get_datasource_from_request(request: Request) -> str:
        datasource = request.get_ascii_input_mandatory("datasource")
        if datasource not in data_source_registry:
            raise MKUserError("datasource", _("The data source '%s' does not exist.") % datasource)

        return datasource

    @staticmethod
    def _get_single_infos_from_request(request: Request) -> SingleInfos:
        single_infos_str = request.get_str_input("single_infos")
        if not single_infos_str:
            return []

        single_infos: SingleInfos = single_infos_str.split(",")
        for key in single_infos:
            if key not in visual_info_registry:
                raise MKUserError("single_infos", _("The info %s does not exist.") % key)

        return single_infos

    @staticmethod
    def _get_original_view_spec_from_request(request: Request) -> ViewSpec:
        view_name = request.get_ascii_input_mandatory("view_name")
        return get_view_by_name(view_name)

    @staticmethod
    def _load_dashboard(owner: UserId, dashboard_name: str) -> DashboardConfig:
        # loading via get_all_dashboards, otherwise the save won't apply the changes
        dashboards = get_all_dashboards()
        key = (owner, dashboard_name)
        if key not in dashboards:
            raise MKUserError(
                "dashboard",
                _("The dashboard '%s' does not exist or you do not have permission to view it.")
                % dashboard_name,
            )

        return dashboards[key]

    def _get_view_spec(
        self,
        request: Request,
        dashboard: DashboardConfig,
        embedded_id: str,
        mode: Mode,
    ) -> ViewSpec:
        view_name = f"{dashboard['name']}_{embedded_id}"
        if mode == "copy":
            view_spec = self._get_original_view_spec_from_request(request).copy()
            view_spec["name"] = view_name
            return view_spec

        if mode == "edit":
            return EmbeddedViewSpecManager.get_embedded_view_spec(dashboard, embedded_id, view_name)

        # create mode
        datasource = self._get_datasource_from_request(request)
        single_infos = self._get_single_infos_from_request(request)
        return self._create_new_view_spec(
            dashboard, embedded_id, view_name, datasource, single_infos
        )

    @staticmethod
    def _create_new_view_spec(
        dashboard: DashboardConfig,
        embedded_id: str,
        view_name: str,
        datasource: str,
        single_infos: SingleInfos,
    ) -> ViewSpec:
        embedded_views = dashboard.get("embedded_views", {})
        if embedded_id in embedded_views:
            raise MKUserError(
                "embedded_id",
                _(
                    "The dashboard '%s' already contains an embedded view with the ID '%s'. "
                    "Please choose another ID."
                )
                % (dashboard["name"], embedded_id),
            )

        return ViewSpec(
            owner=user.ident,
            name=view_name,
            single_infos=single_infos,
            datasource=datasource,
            layout="table",
            group_painters=[],
            painters=[],
            sorters=[],
            browser_reload=0,
            num_columns=1,
            column_headers="off",
            context={},
            add_context_to_title=False,
            title="",
            description="",
            topic="",
            sort_index=0,
            is_show_more=False,
            icon=None,
            hidden=False,
            hidebutton=False,
            public=False,
            packaged=False,
            link_from={},
            main_menu_search_terms=[],
        )
