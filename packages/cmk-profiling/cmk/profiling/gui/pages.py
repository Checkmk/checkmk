#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""WATO pages for viewing stored performance profiles and flamegraphs."""

from __future__ import annotations

import json
import pstats
import tempfile
from collections.abc import Collection
from dataclasses import asdict
from typing import override

import cmk.utils.paths
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.confirm_links import make_confirm_delete_link
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.profiling.backend import (
    build_flamegraph_tree,
    get_function_paths,
    get_summary_stats,
    get_top_hotspots,
)
from cmk.profiling.gui._store import (
    PROFILE_ID_RE,
    ProfileStore,
    retention_kwargs,
)
from cmk.shared_typing.profiling_flamegraph import (
    ProfileMetadata as WireProfileMetadata,
)
from cmk.shared_typing.profiling_flamegraph import ProfilingFlamegraphData
from cmk.web.utils.urls import makeactionuri_contextless, makeuri_contextless

# Upload cap — 10 MB is generous for a cProfile dump (typical request profiles
# are <1 MB). A tighter limit reduces the worst-case size of bytes fed into
# marshal.load().
_MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Form id contract with the Vue app: the Python side renders <form
# id="form_upload_profile"> and the Vue drag-drop UI submits it by id. Keep
# both sides in sync.
_UPLOAD_FORM_ID = "form_upload_profile"
_UPLOAD_INPUT_ID = "_profile_file"


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
) -> None:
    page_registry.register(PageEndpoint("profile_download", PageProfileDownload()))
    page_registry.register(PageEndpoint("profile_data", PageProfileData()))
    mode_registry.register(ModePerformanceProfiles)
    mode_registry.register(ModeProfileFlamegraph)


def _feature_enabled(config: Config) -> bool:
    return bool(config.profiling_options.get("enabled", False))


def _require_feature_enabled(config: Config) -> None:
    if not _feature_enabled(config):
        raise MKUserError(
            None,
            _(
                "Performance profiles are disabled. Enable them in Global settings > "
                "Developer Tools > Performance profiles."
            ),
        )


class ModePerformanceProfiles(WatoMode[None]):
    @classmethod
    @override
    def name(cls) -> str:
        return "performance_profiles"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["performance_profiles"]

    @override
    def title(self) -> str:
        return _("Performance profiles")

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        max_age_days = retention_kwargs(config.profiling_options)["max_age_days"]
        if max_age_days is None:
            housekeeping_title = _("Housekeeping (enforce count)")
            housekeeping_message = _("Trim the profile store to the configured maximum count?")
        else:
            housekeeping_title = _("Housekeeping (> %(days)d days)") % {"days": max_age_days}
            housekeeping_message = _(
                "Remove all profiles older than %(days)d days and trim to the "
                "configured maximum count?"
            ) % {"days": max_age_days}

        delete_all_url = make_confirm_delete_link(
            i18n=_,
            url=makeactionuri_contextless(
                request,
                transactions.get(),
                [("mode", self.name()), ("_action", "delete_all")],
                filename="wato.py",
            ),
            title=_("Delete all profiles"),
            message=_("Do you really want to delete all stored profiles?"),
        )
        housekeeping_url = make_confirm_delete_link(
            i18n=_,
            url=makeactionuri_contextless(
                request,
                transactions.get(),
                [("mode", self.name()), ("_action", "housekeeping")],
                filename="wato.py",
            ),
            title=_("Run housekeeping"),
            message=housekeeping_message,
            confirm_button=_("Remove"),
        )

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Cleanup"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Delete all profiles"),
                                    icon_name=StaticIcon(IconNames.delete),
                                    item=make_simple_link(delete_all_url),
                                ),
                                PageMenuEntry(
                                    title=housekeeping_title,
                                    icon_name=StaticIcon(IconNames.cleanup),
                                    item=make_simple_link(housekeeping_url),
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Support diagnostics"),
                                    icon_name=StaticIcon(IconNames.diagnostics),
                                    item=make_simple_link("wato.py?mode=diagnostics"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    @override
    def action(self, config: Config) -> ActionResult:
        check_csrf_token()
        if not transactions.check_transaction(request):
            return None

        _require_feature_enabled(config)

        store = ProfileStore(cmk.utils.paths.profiles_dir)
        action_var = request.get_str_input("_action")

        if action_var == "delete":
            profile_id = request.get_ascii_input_mandatory("_delete")
            _validate_profile_id(profile_id)
            if store.delete_profile(profile_id):
                html.show_message(_("Profile %(id)s deleted.") % {"id": profile_id})

        elif action_var == "delete_all":
            count = store.delete_all_profiles()
            html.show_message(_("%(count)d profiles deleted.") % {"count": count})

        elif action_var == "housekeeping":
            count = store.housekeeping(**retention_kwargs(config.profiling_options))
            html.show_message(_("Housekeeping: %(count)d old profiles removed.") % {"count": count})

        elif action_var == "upload":
            try:
                _handle_profile_upload(store)
            except MKUserError as exc:
                # Surface the parse error to the next page render via a query
                # param; the Vue component turns it into a CmkAlertBox instead
                # of the framework's default red error bar.
                return redirect(
                    makeuri_contextless(
                        request,
                        [("mode", self.name()), ("_upload_error", str(exc))],
                        filename="wato.py",
                    )
                )

        return redirect(ModePerformanceProfiles.mode_url())

    @override
    def page(self, config: Config) -> None:
        _require_feature_enabled(config)

        store = ProfileStore(cmk.utils.paths.profiles_dir)
        # Reconcile retention on the page-load path (admin-initiated, not per
        # request). Also cleans up orphan .profile files left by partial writes.
        store.housekeeping(**retention_kwargs(config.profiling_options))
        profiles = store.list_profiles()
        upload_error = request.get_str_input_mandatory("_upload_error", "")

        _render_upload_form()

        profiles_data = []
        for profile in profiles:
            profiles_data.append(
                {
                    **asdict(profile),
                    "flamegraph_url": makeuri_contextless(
                        request,
                        [("mode", "profile_flamegraph"), ("profile_id", profile.profile_id)],
                        filename="wato.py",
                    ),
                    "download_url": makeuri_contextless(
                        request,
                        [("profile_id", profile.profile_id)],
                        filename="profile_download.py",
                    ),
                    "delete_url": make_confirm_delete_link(
                        i18n=_,
                        url=makeactionuri_contextless(
                            request,
                            transactions.get(),
                            [
                                ("mode", self.name()),
                                ("_action", "delete"),
                                ("_delete", profile.profile_id),
                            ],
                            filename="wato.py",
                        ),
                        title=_("Delete profile"),
                        suffix=profile.profile_id,
                        message=_("Source: %(source)s") % {"source": profile.source_info},
                    ),
                }
            )

        html.vue_component(
            "cmk-profiling-profiles-list",
            data={
                "profiles": profiles_data,
                "upload_form_id": _UPLOAD_FORM_ID,
                "upload_input_id": _UPLOAD_INPUT_ID,
                "upload_error": upload_error,
            },
        )


class ModeProfileFlamegraph(WatoMode[None]):
    """Displays a flamegraph SVG inline within the Checkmk GUI frame."""

    @classmethod
    @override
    def name(cls) -> str:
        return "profile_flamegraph"

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModePerformanceProfiles

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["performance_profiles"]

    @override
    def _from_vars(self) -> None:
        self._profile_id = request.get_str_input_mandatory("profile_id")
        _validate_profile_id(self._profile_id)
        self._store = ProfileStore(cmk.utils.paths.profiles_dir)

    @override
    def title(self) -> str:
        return _("Flamegraph: %(id)s") % {"id": self._profile_id}

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        dl_url = makeuri_contextless(
            request,
            [("profile_id", self._profile_id)],
            filename="profile_download.py",
        )

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Profile"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Download .profile"),
                                    icon_name=StaticIcon(IconNames.download),
                                    item=make_simple_link(dl_url),
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=[
                                PageMenuEntry(
                                    title=_("All profiles"),
                                    icon_name=StaticIcon(IconNames.diagnostics),
                                    item=make_simple_link("wato.py?mode=performance_profiles"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    @override
    def action(self, config: Config) -> ActionResult:
        return None

    @override
    def page(self, config: Config) -> None:
        _require_feature_enabled(config)

        if self._store.get_profile(self._profile_id) is None:
            html.show_error(_("Profile not found."))
            return
        data_url = makeuri_contextless(
            request,
            [("profile_id", self._profile_id)],
            filename="profile_data.py",
        )
        html.vue_component(
            "cmk-profiling-flamegraph",
            data={"profile_id": self._profile_id, "data_url": data_url},
        )


class PageProfileData(Page):
    """Returns the flamegraph's heavy payload (tree + hotspots + summary) as JSON.

    Splitting this from the WATO page render keeps the initial page fast: the
    Vue shell shows a skeleton while this endpoint computes the tree, which
    can take seconds for large profiles.
    """

    @override
    def page(self, ctx: PageContext) -> None:
        if not user.may("wato.performance_profiles"):
            raise MKAuthException(_("Sorry, you lack the permission for profile data."))
        _require_feature_enabled(ctx.config)

        profile_id = request.get_str_input_mandatory("profile_id")
        _validate_profile_id(profile_id)

        store = ProfileStore(cmk.utils.paths.profiles_dir)
        profile_path = store.get_profile(profile_id)
        response.set_content_type("application/json")
        if profile_path is None:
            response.status_code = 404
            response.set_data(json.dumps({"error": "Profile not found"}))
            return

        stats = pstats.Stats(str(profile_path))
        meta = store.get_metadata(profile_id)
        total_calls, total_functions = get_summary_stats(stats)
        hotspots = get_top_hotspots(profile_path, stats=stats)
        tree_node, total_time = build_flamegraph_tree(profile_path, stats=stats)
        function_paths = get_function_paths(stats)

        payload = ProfilingFlamegraphData(
            # The on-disk ProfileMetadata (cmk.profiling.backend) and the wire
            # ProfileMetadata share the same fields; copy across the layer boundary
            # so the persistence model stays independent of the frontend contract.
            metadata=(
                WireProfileMetadata(
                    profile_id=meta.profile_id,
                    source_type=meta.source_type,
                    source_info=meta.source_info,
                    duration_ms=meta.duration_ms,
                    timestamp=meta.timestamp,
                )
                if meta is not None
                else None
            ),
            hotspots=hotspots,
            flamegraph_tree=tree_node,
            function_paths=function_paths,
            total_time=total_time,
            total_calls=total_calls,
            total_functions=total_functions,
        )
        response.set_data(json.dumps(asdict(payload)))


class PageProfileDownload(Page):
    """Serves the raw .profile file for download."""

    @override
    def page(self, ctx: PageContext) -> None:
        if not user.may("wato.performance_profiles"):
            raise MKAuthException(_("Sorry, you lack the permission for downloading profile data."))
        _require_feature_enabled(ctx.config)

        profile_id = request.get_str_input_mandatory("profile_id")
        _validate_profile_id(profile_id)

        store = ProfileStore(cmk.utils.paths.profiles_dir)
        profile_path = store.get_profile(profile_id)
        if profile_path is None:
            raise MKUserError("profile_id", _("Profile not found."))

        response.set_content_type("application/octet-stream")
        # Bypass response.set_content_disposition(): its FILE_EXTENSIONS
        # whitelist doesn't cover .profile, and profile_id is constrained by
        # _validate_profile_id to [0-9a-f_], so direct interpolation is safe.
        response.headers["Content-Disposition"] = f'attachment; filename="{profile_id}.profile"'
        response.set_data(profile_path.read_bytes())


def _render_upload_form() -> None:
    """Render a hidden form that the Vue upload component will submit.

    The <form> and <input type="file"> are rendered on the Python side so the
    existing CSRF/multipart handling keeps working unchanged. The Vue drag-drop
    component attaches to both by id. IDs are passed into the Vue component as
    props (see ModePerformanceProfiles.page) to make the contract explicit.
    """
    html.begin_form("upload_profile", method="POST")
    html.hidden_field("_action", "upload")
    html.hidden_fields()
    html.input(
        name=_UPLOAD_INPUT_ID,
        id_=_UPLOAD_INPUT_ID,
        type_="file",
        style="display:none",
    )
    html.end_form()


def _handle_profile_upload(store: ProfileStore) -> None:
    # uploaded_file() raises MKUserError if no file was selected
    file_name, _mime_type, file_content = request.uploaded_file(_UPLOAD_INPUT_ID)

    if len(file_content) > _MAX_UPLOAD_SIZE:
        raise MKUserError(
            _UPLOAD_INPUT_ID,
            _("File too large (max %(limit)d MB).") % {"limit": _MAX_UPLOAD_SIZE // (1024 * 1024)},
        )

    try:
        _validate_profile_data(file_content)
    except Exception as exc:
        raise MKUserError(
            _UPLOAD_INPUT_ID,
            _("Could not parse '%(file)s' as a cProfile file: %(error)s")
            % {"file": file_name, "error": exc},
        )

    profile_id = store.save_uploaded(file_content, file_name)
    html.show_message(_("Profile %(id)s uploaded and analyzed.") % {"id": profile_id})


# cProfile / pstats dumps are marshal-encoded dicts; marshal's type byte for a
# dict is 0x7B (ASCII '{'), optionally OR'd with the 0x80 ref flag. Refuse
# anything else before handing the bytes to pstats.Stats → marshal.load, which
# is unsafe on fully untrusted input. The feature gate and admin permission are
# the primary defences; this is belt-and-braces.
_MARSHAL_DICT_MAGIC = 0x7B


def _validate_profile_data(content: bytes) -> None:
    """Fail fast if the bytes aren't a marshalled dict, then round-trip pstats.

    ``pstats.Stats`` eventually calls ``marshal.load`` on the file, which only
    deserialises a fixed set of simple types but has historically had
    RCE-adjacent CVEs on malformed input. The feature is gated behind a
    per-site enable flag and the performance-profiles permission; this check adds
    a cheap shape gate so the happy path is the only one reaching marshal.
    """
    if not content or (content[0] & 0x7F) != _MARSHAL_DICT_MAGIC:
        raise ValueError("not a cProfile dump (missing marshal dict header)")
    with tempfile.NamedTemporaryFile(suffix=".profile") as tmp:
        tmp.write(content)
        tmp.flush()
        pstats.Stats(tmp.name)


def _validate_profile_id(profile_id: str) -> None:
    """Prevent path traversal and injection."""
    if not PROFILE_ID_RE.match(profile_id):
        raise MKUserError("profile_id", _("Invalid profile ID"))
