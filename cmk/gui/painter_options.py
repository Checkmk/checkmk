#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import time
from collections.abc import Sequence
from typing import Any, override

from cmk.ccc.plugin_registry import Registry

import cmk.utils.render

from cmk.gui import forms, valuespec
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ViewSpec
from cmk.gui.valuespec import DropdownChoice, ValueSpec
from cmk.gui.view_utils import CellSpec


def register(painter_option_registry_: PainterOptionRegistry) -> None:
    painter_option_registry.register(PainterOptionRefresh())
    painter_option_registry.register(PainterOptionNumColumns())


class PainterOption(abc.ABC):
    def __init__(self, ident: str, valuespec: ValueSpec | None = None) -> None:
        self.ident = ident
        self._valuespec = valuespec
        self.request = request
        self.config = active_config

    @property
    def valuespec(self) -> ValueSpec:
        """Use this getter when active_config is required for valuespecs, else use the init paramater"""
        if not self._valuespec:
            raise NotImplementedError()
        return self._valuespec


# TODO: Better name it PainterOptions or DisplayOptions? There are options which only affect
# painters, but some which affect generic behaviour of the views, so DisplayOptions might
# be better.
class PainterOptions:
    """Painter options are settings that can be changed per user per view.
    These options are controlled throught the painter options form which
    is accessible through the small monitor icon on the top left of the
    views."""

    # TODO: We should have some View instance that uses an object of this class as helper instead,
    #       but this would be a bigger change involving a lot of view rendering code.
    @classmethod
    @request_memoize()
    def get_instance(cls) -> PainterOptions:
        """Return the request bound instance"""
        return cls()

    def __init__(self) -> None:
        super().__init__()
        # The names of the painter options used by the current view
        self._used_option_names: Sequence[str] = []
        # The effective options for this view
        self._options: dict[str, Any] = {}

    def load(self, view_name: str | None = None) -> None:
        self._load_from_config(view_name)

    def _load_from_config(self, view_name: str | None) -> None:
        if self._is_anonymous_view(view_name):
            return  # never has options

        if not self.painter_options_permitted():
            return

        # Options are stored per view. Get all options for all views
        vo = user.load_file("viewoptions", {})
        self._options = vo.get(view_name, {})

    def _is_anonymous_view(self, view_name: str | None) -> bool:
        return view_name is None

    def save_to_config(self, view_name: str) -> None:
        vo = user.load_file("viewoptions", {}, lock=True)
        vo[view_name] = self._options
        user.save_file("viewoptions", vo)

    def update_from_url(self, view_name: str, used_option_names: Sequence[str]) -> None:
        self._used_option_names = used_option_names

        if not self.painter_option_form_enabled():
            return

        if request.has_var("_reset_painter_options"):
            self._clear_painter_options(view_name)
            return

        if request.has_var("_update_painter_options"):
            self._set_from_submitted_form(view_name)

    def _set_from_submitted_form(self, view_name: str) -> None:
        # TODO: Remove all keys that are in painter_option_registry
        # but not in self._used_option_names

        modified = False
        for option_name in self._used_option_names:
            # Get new value for the option from the value spec
            vs = self.get_valuespec_of(option_name)
            value = vs.from_html_vars("po_%s" % option_name)

            if not self._is_set(option_name) or self.get(option_name) != value:
                modified = True

            self.set(option_name, value)

        if modified:
            self.save_to_config(view_name)

    def _clear_painter_options(self, view_name: str) -> None:
        # TODO: This never removes options that are not existant anymore
        modified = False
        for name in painter_option_registry.keys():
            try:
                del self._options[name]
                modified = True
            except KeyError:
                pass

        if modified:
            self.save_to_config(view_name)

        # Also remove the options from current html vars. Otherwise the
        # painter option form will display the just removed options as
        # defaults of the painter option form.
        for varname, _value in list(request.itervars(prefix="po_")):
            request.del_var(varname)

    def get_valuespec_of(self, name: str) -> ValueSpec:
        return painter_option_registry[name].valuespec

    def _is_set(self, name: str) -> bool:
        return name in self._options

    # Sets a painter option value (only for this request). Is not persisted!
    def set(self, name: str, value: Any) -> None:
        self._options[name] = value

    # Returns either the set value, the provided default value or if none
    # provided, it returns the default value of the valuespec.
    def get(self, name: str, dflt: Any = None) -> Any:
        if dflt is None:
            try:
                dflt = self.get_valuespec_of(name).default_value()
            except KeyError:
                # Some view options (that are not declared as display options)
                # like "refresh" don't have a valuespec. So they need to default
                # to None.
                # TODO: Find all occurrences and simply declare them as "invisible"
                # painter options.
                pass
        return self._options.get(name, dflt)

    # Not falling back to a default value, simply returning None in case
    # the option is not set.
    def get_without_default(self, name: str) -> Any:
        return self._options.get(name)

    def get_all(self) -> dict[str, Any]:
        return self._options

    def painter_options_permitted(self) -> bool:
        return user.may("general.painter_options")

    def painter_option_form_enabled(self) -> bool:
        return bool(self._used_option_names) and self.painter_options_permitted()

    def show_form(self, view_spec: ViewSpec, used_option_names: Sequence[str]) -> None:
        self._used_option_names = used_option_names

        if not display_options.enabled(display_options.D) or not self.painter_option_form_enabled():
            return

        with html.form_context("painteroptions"):
            forms.header("", show_table_head=False)
            for name in self._used_option_names:
                vs = self.get_valuespec_of(name)
                forms.section(vs.title())
                if name == "refresh":
                    vs.render_input("po_%s" % name, view_spec.get("browser_reload", self.get(name)))
                    continue
                vs.render_input("po_%s" % name, self.get(name, view_spec.get(name)))
            forms.end()

            html.button(varname="_update_painter_options", title=_("Submit"), cssclass="hot submit")
            html.button(varname="_reset_painter_options", title=_("Reset"), cssclass="submit")

            html.hidden_fields()


class PainterOptionRegistry(Registry[PainterOption]):
    @override
    def plugin_name(self, instance: PainterOption) -> str:
        return instance.ident


painter_option_registry = PainterOptionRegistry()


class PainterOptionRefresh(PainterOption):
    def __init__(self) -> None:
        super().__init__(ident="refresh")

    @override
    @property
    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Refresh interval"),
            choices=[
                (x, {0: _("off")}.get(x, str(x) + "s")) for x in self.config.view_option_refreshes
            ],
        )


class PainterOptionNumColumns(PainterOption):
    def __init__(self) -> None:
        super().__init__(ident="num_columns")

    @override
    @property
    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Entries per row"),
            choices=[(x, str(x)) for x in self.config.view_option_columns],
        )


def get_graph_timerange_from_painter_options() -> tuple[int, int]:
    # Function has a single caller.
    painter_options = PainterOptions.get_instance()
    value = painter_options.get("pnp_timerange")
    vs = painter_options.get_valuespec_of("pnp_timerange")
    assert isinstance(vs, valuespec.Timerange)
    start_time, end_time = vs.compute_range(value)[0]
    return int(start_time), int(end_time)


def paint_age_or_never(
    timestamp: int,
    has_been_checked: bool,
    bold_if_younger_than: int,
    *,
    request: Request,
    painter_options: PainterOptions,
    mode: str | None = None,
    what: str = "past",
) -> CellSpec:
    if mode is None:
        mode = request.var("po_ts_format", painter_options.get("ts_format"))

    if timestamp == 0 and has_been_checked and (mode in {"abs", "mixed"}):
        return "age", _("Never")

    return paint_age(
        timestamp,
        has_been_checked,
        bold_if_younger_than,
        request=request,
        painter_options=painter_options,
        mode=mode,
        what=what,
    )


def paint_age(
    timestamp: int,
    has_been_checked: bool,
    bold_if_younger_than: int,
    *,
    request: Request,
    painter_options: PainterOptions,
    mode: str | None = None,
    what: str = "past",
) -> CellSpec:
    if not has_been_checked:
        return "age", "-"

    if mode is None:
        mode = request.var("po_ts_format", painter_options.get("ts_format"))

    if mode == "epoch":
        return "", str(int(timestamp))

    if mode == "both":
        css, h1 = paint_age(
            timestamp,
            has_been_checked,
            bold_if_younger_than,
            request=request,
            painter_options=painter_options,
            mode="abs",
            what=what,
        )
        css, h2 = paint_age(
            timestamp,
            has_been_checked,
            bold_if_younger_than,
            request=request,
            painter_options=painter_options,
            mode="rel",
            what=what,
        )
        return css, f"{h1} - {h2}"

    age = time.time() - timestamp
    if mode == "abs" or (mode == "mixed" and abs(age) >= 48 * 3600):
        dateformat = request.var("po_ts_date", painter_options.get("ts_date"))
        assert dateformat is not None
        return "age", time.strftime(dateformat + " %H:%M:%S", time.localtime(timestamp))

    warn_txt = ""
    output_format = "%s"
    if what == "future" and age > 0:
        warn_txt = " <b>%s</b>" % _("in the past!")
    elif what == "past" and age < 0:
        warn_txt = " <b>%s</b>" % _("in the future!")
    elif what == "both" and age > 0:
        output_format = "%%s %s" % _("ago")

    # Time delta less than two days => make relative time
    if age < 0:
        age = -age
        prefix = "in "
    else:
        prefix = ""
    if age < bold_if_younger_than:
        age_class = "age recent"
    else:
        age_class = "age"

    return age_class, prefix + (output_format % cmk.utils.render.approx_age(age)) + warn_txt
