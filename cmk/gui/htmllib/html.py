#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

from __future__ import annotations

import contextlib
import json
import pprint
import re
import time
import typing
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import lru_cache
from typing import Any, Literal

from flask import current_app, session

import cmk.ccc.version as cmk_version

import cmk.utils.paths

from cmk.gui import log, utils
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu_entry import enable_page_menu_entry
from cmk.gui.theme import Theme
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    Choice,
    ChoiceGroup,
    ChoiceId,
    ChoiceText,
    CSSSpec,
    GroupedChoices,
    Icon,
)
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.popups import PopupMethod
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import doc_reference_url, DocReference, requested_file_name
from cmk.gui.utils.user_errors import user_errors

from .generator import HTMLWriter
from .tag_rendering import (
    HTMLContent,
    HTMLTagAttributes,
    HTMLTagAttributeValue,
    HTMLTagValue,
    render_element,
    render_end_tag,
    render_start_tag,
)
from .type_defs import RequireConfirmation


class _Manifest(typing.NamedTuple):
    main: str
    main_stylesheets: list[str]
    stage1: str


def inject_js_profiling_code():
    return active_config.inject_js_profiling_code or html.request.has_var(
        "inject_js_profiling_code"
    )


EncType = typing.Literal[
    "application/x-url-encoded",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
]


class HTMLGenerator(HTMLWriter):
    def __init__(
        self,
        request: Request,
        output_funnel: OutputFunnel,
        output_format: str,
        mobile: bool,
    ) -> None:
        super().__init__(output_funnel, output_format, mobile)

        self._logger = log.logger.getChild("html")
        self._header_sent = False
        self._body_classes = ["main"]
        self.have_help = False

        # Forms
        self.form_name: str | None = None
        self.form_vars: list[str] = []
        self.form_has_submit_button: bool = False

        self.request = request

    @property
    def screenshotmode(self) -> bool:
        """Enabling the screenshot mode omits the fancy background and makes it white instead."""
        return bool(self.request.var("screenshotmode", "1" if active_config.screenshotmode else ""))

    def set_focus(self, varname: str) -> None:
        self.final_javascript(
            f"cmk.utils.set_focus_by_name({json.dumps(self.form_name)}, {json.dumps(varname)})"
        )

    def set_focus_by_id(self, dom_id: str) -> None:
        self.final_javascript("cmk.utils.set_focus_by_id(%s)" % (json.dumps(dom_id)))

    def immediate_browser_redirect(self, secs: float, url: str) -> None:
        self.javascript(f"cmk.utils.set_reload({secs}, '{url}');")

    def add_body_css_class(self, cls: str) -> None:
        self._body_classes.append(cls)

    def reload_whole_page(self, url: str | None = None) -> None:
        if not self.request.has_var("_ajaxid"):
            return self.final_javascript("cmk.utils.reload_whole_page(%s)" % json.dumps(url))
        return None

    def show_localization_hint(self) -> None:
        url = "wato.py?mode=edit_configvar&varname=user_localizations"
        self._write(
            self._render_message(
                HTMLWriter.render_sup("*")
                + escaping.escape_to_html_permissive(
                    _(
                        "These texts may be localized depending on the users' "
                        "language. You can configure the localizations "
                        "<a href='%s'>in the global settings</a>."
                    )
                    % url,
                    escape_links=False,
                ),
                "message",
            )
        )

    def help(self, text: None | HTML | str) -> None:
        """Embed help box, whose visibility is controlled by a global button in the page.

        You may add macros like this to the help texts to create links to the user
        manual: [piggyback|Piggyback chapter].
        All such documentation references must be added to or included in the class DocReference.
        """
        self.write_html(self.render_help(text))

    def render_help(self, text: None | HTML | str) -> HTML:
        if isinstance(text, str):
            text = escaping.escape_text(text)
        elif isinstance(text, HTML):
            text = "%s" % text

        if not text:
            return HTML.empty()

        stripped: str = text.strip()
        if not stripped:
            return HTML.empty()

        help_text = HTML.without_escaping(self.resolve_help_text_macros(stripped))

        self.enable_help_toggle()
        inner_html: HTML = HTMLWriter.render_div(self.render_icon("info"), class_="info_icon")
        inner_html += HTMLWriter.render_div(help_text, class_="help_text")
        return HTMLWriter.render_div(inner_html, class_="help")

    @staticmethod
    def resolve_help_text_macros(text: str) -> str:
        # text = ".*[<page_name>#<anchor_name>|<link_title>].*"
        # e.g. text = "[intro_setup#install|Welcome]" returns
        #      <a href="https://docs.checkmk.com/master/en/intro_setup.html#install">Welcome</a>
        urls: list[str | None] = []
        if matches := re.findall(r"(\[([a-z0-9_-]+#?[a-z0-9_-]+|)\|([^\]]+)\])", text):
            for match in matches:
                try:
                    doc_ref: DocReference = DocReference(match[1])
                    urls.append(doc_reference_url(doc_ref=doc_ref))
                except ValueError:
                    urls.append(None)

        for n, match in enumerate(matches):
            if not urls[n]:
                text = text.replace(match[0], match[2])
            else:
                text = text.replace(match[0], f'<a href="{urls[n]}" target="_blank">{match[2]}</a>')
        return text

    def enable_help_toggle(self) -> None:
        self.have_help = True

    def debug(self, *x: Any) -> None:
        for element in x:
            try:
                formatted = pprint.pformat(element)
            except UnicodeDecodeError:
                formatted = repr(element)
            self._write(HTMLWriter.render_pre(formatted))

    def default_html_headers(self) -> None:
        self.meta(httpequiv="Content-Type", content="text/html; charset=utf-8")
        self.write_html(
            render_start_tag(
                "link",
                rel="shortcut icon",
                href=theme.url("images/favicon.ico"),
                type_="image/ico",
                close_tag=True,
            )
        )

    def _head(self, title: str, javascripts: Sequence[str] | None = None) -> None:
        javascripts = javascripts if javascripts else []

        self.open_head()
        if inject_js_profiling_code():
            self._inject_profiling_code()

        self.default_html_headers()
        self.title(title)

        # If the variable _link_target is set, then all links in this page
        # should be targeted to the HTML frame named by _link_target.
        # This is e.g. useful in the dashboard
        if self.link_target:
            self.base(target=self.link_target)

        font_css_filepath = "themes/facelift/fonts_inter.css"
        css_filepath = theme.url("theme.css")

        if current_app.debug and not current_app.testing:
            HTMLGenerator._verify_file_exists_in_web_dirs(css_filepath)
            HTMLGenerator._verify_file_exists_in_web_dirs(font_css_filepath)
        self.stylesheet(HTMLGenerator._append_cache_busting_query(font_css_filepath))
        self.stylesheet(HTMLGenerator._append_cache_busting_query(css_filepath))

        self._add_custom_style_sheet()

        # Load all scripts
        for js in javascripts:
            js_filepath = f"js/{js}_min.js"
            js_url = HTMLGenerator._append_cache_busting_query(js_filepath)
            if current_app.debug and not current_app.testing:
                HTMLGenerator._verify_file_exists_in_web_dirs(js_filepath)
            self.javascript_file(js_url)

        self._inject_vue_frontend()

        self.set_js_csrf_token()

        if self.browser_reload != 0.0:
            self.javascript(f"cmk.utils.set_reload({self.browser_reload})")

        self.close_head()

    @lru_cache
    def _load_vue_manifest(self) -> _Manifest:
        base = cmk.utils.paths.web_dir / "htdocs/cmk-frontend-vue"
        with (base / ".manifest.json").open() as fo:
            manifest = json.load(fo)

        main = f"cmk-frontend-vue/{manifest['src/main.ts']['file']}"
        main_stylesheets = manifest["src/main.ts"]["css"]
        stage1 = f"cmk-frontend-vue/{manifest['src/stage1.ts']['file']}"
        return _Manifest(main, main_stylesheets, stage1)

    def _inject_vue_frontend(self):
        manifest = self._load_vue_manifest()
        if active_config.load_frontend_vue == "inject":
            # stage1 will try to load the hot reloading files. if this fails,
            # an error will be shown and the fallback files will be loaded.
            self.js_entrypoint(
                json.dumps({"fallback": [manifest.main]}),
                type_="cmk-entrypoint-vue-stage1",
            )
            self.javascript_file(manifest.stage1)
        else:
            # production setup
            self.javascript_file(manifest.main, type_="module")
            for stylesheet in manifest.main_stylesheets:
                self.stylesheet(f"cmk-frontend-vue/{stylesheet}")

    def _inject_profiling_code(self):
        self.javascript("const startTime = Date.now();")
        # A lambda, so it will get evaluated at the end of the request, not the beginning.
        self.final_javascript(
            lambda: f"""
                const generationDuration = {round((time.monotonic() - self.request.started) * 1000, 0)};
                const currentUrl = window.location.pathname + window.location.search;
                document.addEventListener(
                    'DOMContentLoaded',
                    function() {{
                        activate_tracking(currentUrl, startTime, generationDuration);
                    }}
                );
            """
        )
        self.javascript_file(HTMLGenerator._append_cache_busting_query("js/tracking_entry_min.js"))

    def set_js_csrf_token(self) -> None:
        # session is LocalProxy, only on access it is None, so we cannot test on 'is None'
        if not hasattr(session, "session_info"):
            return
        self.javascript(
            "var global_csrf_token = %s;" % (json.dumps(session.session_info.csrf_token))
        )

    def _add_custom_style_sheet(self) -> None:
        for css in HTMLGenerator._plugin_stylesheets():
            self._write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)

        if active_config.custom_style_sheet:
            self._write(
                '<link rel="stylesheet" type="text/css" href="%s">\n'
                % active_config.custom_style_sheet
            )

    @staticmethod
    def _plugin_stylesheets() -> Iterable[str]:
        plugin_stylesheets = set()
        for directory in [
            cmk.utils.paths.web_dir / "htdocs/css",
            cmk.utils.paths.local_web_dir / "htdocs/css",
        ]:
            if directory.exists():
                for entry in directory.iterdir():
                    if entry.suffix == ".css":
                        plugin_stylesheets.add(entry.name)
        return plugin_stylesheets

    @staticmethod
    def _verify_file_exists_in_web_dirs(file_path: str) -> None:
        path = cmk.utils.paths.web_dir / "htdocs" / file_path
        local_path = cmk.utils.paths.local_web_dir / "htdocs" / file_path
        file_missing = not (path.exists() or local_path.exists())
        if file_missing:
            raise FileNotFoundError(f"Neither {path} nor {local_path} exist.")

    @staticmethod
    def _append_cache_busting_query(filename: str) -> str:
        return f"{filename}?v={cmk_version.__version__}"

    def html_head(
        self,
        title: str,
        main_javascript: str = "main",
        force: bool = False,
    ) -> None:
        javascript_files = [main_javascript]
        if force or not self._header_sent:
            self.write_html(HTML.without_escaping("<!DOCTYPE HTML>\n"))
            self.open_html()
            self._head(title, javascript_files)
            self._header_sent = True

    def body_start(
        self,
        title: str = "",
        main_javascript: Literal["main", "side"] = "main",
        force: bool = False,
    ) -> None:
        self.html_head(title, main_javascript, force)
        self.open_body(class_=self._get_body_css_classes(), data_theme=theme.get())

    def _get_body_css_classes(self) -> list[str]:  # TODO: Sequence!
        classes = self._body_classes[:]
        if self.screenshotmode:
            classes += ["screenshotmode"]
        if user.inline_help_as_text:
            classes += ["inline_help_as_text"]
        return classes

    def html_foot(self) -> None:
        self.close_html()

    def footer(self, show_body_end: bool = True) -> None:
        if self.output_format != "html":
            return

        self.end_page_content()

        if show_body_end:
            self.body_end()

    def focus_here(self) -> None:
        self.a("", href="#focus_me", id_="focus_me")
        self.set_focus_by_id("focus_me")

    def body_end(self) -> None:
        if self.have_help:
            enable_page_menu_entry(self, "inline_help")
        self.write_final_javascript()
        self.javascript("cmk.visibility_detection.initialize();")
        self.close_body()
        self.close_html()

    @contextlib.contextmanager
    def form_context(
        self,
        name: str,
        action: str | None = None,
        method: str = "GET",
        onsubmit: str | None = None,
        add_transid: bool = True,
        require_confirmation: RequireConfirmation | None = None,
        confirm_on_leave: bool = False,
        only_close: bool = False,
    ) -> typing.Iterator[None]:
        html.begin_form(
            name=name,
            action=action,
            method=method,
            onsubmit=onsubmit,
            add_transid=add_transid,
            require_confirmation=require_confirmation,
            confirm_on_leave=confirm_on_leave,
        )

        try:
            yield
        finally:
            if only_close:
                html.close_form()
            else:
                html.end_form()

    def begin_form(
        self,
        name: str,
        action: str | None = None,
        method: str = "GET",
        onsubmit: str | None = None,
        add_transid: bool = True,
        require_confirmation: RequireConfirmation | None = None,
        confirm_on_leave: bool = False,
    ) -> None:
        self.form_name = name
        self.form_vars = []
        self.form_has_submit_button = False

        data_cmk_form_confirmation = None
        if require_confirmation:
            data_cmk_form_confirmation = require_confirmation.serialize()

        if action is None:
            action = requested_file_name(self.request) + ".py"

        enctype: EncType = "multipart/form-data"

        if confirm_on_leave:
            html.open_ts_container(
                container="form",
                id_="form_%s" % name,
                function_name="confirm_on_form_leave",
                name=name,
                class_=name,
                action=action,
                method=method,
                onsubmit=onsubmit,
                data_cmk_form_confirmation=data_cmk_form_confirmation,
                enctype=enctype if method.lower() == "post" else None,
            )
        else:
            self.open_form(
                id_="form_%s" % name,
                name=name,
                class_=name,
                action=action,
                method=method,
                onsubmit=onsubmit,
                data_cmk_form_confirmation=data_cmk_form_confirmation,
                enctype=enctype if method.lower() == "post" else None,
            )

        if hasattr(session, "session_info"):
            self.hidden_field("_csrf_token", session.session_info.csrf_token)

        self.hidden_field("filled_in", name, add_var=True)
        if add_transid:
            self.hidden_field(
                "_transid",
                str(transactions.get()),
                add_var=True,
            )

    def end_form(self) -> None:
        if not self.form_has_submit_button:
            self.input(name="_save", type_="submit", cssclass="hidden_submit")
        self.close_form()
        self.form_name = None

    def in_form(self) -> bool:
        return self.form_name is not None

    def prevent_password_auto_completion(self) -> None:
        # These fields are not really used by the form. They are used to prevent the browsers
        # from filling the default password and previous input fields in the form
        # with password which are eventually saved in the browsers password store.
        self.input(name=None, type_="text", style="display:none;")
        self.input(name=None, type_="password", style="display:none;")

    # Needed if input elements are put into forms without the helper
    # functions of us. TODO: Should really be removed and cleaned up!
    def add_form_var(self, varname: str) -> None:
        self.form_vars.append(varname)

    # Beware: call this method just before end_form(). It will
    # add all current non-underscored HTML variables as hiddedn
    # field to the form - *if* they are not used in any input
    # field. (this is the reason why you must not add any further
    # input fields after this method has been called).
    def hidden_fields(
        self, varlist: Sequence[str] | None = None, add_action_vars: bool = False
    ) -> None:
        if varlist is not None:
            for var in varlist:
                self.hidden_field(var, self.request.var(var, ""))
        else:  # add *all* get variables, that are not set by any input!
            for var, _val in self.request.itervars():
                if var not in self.form_vars and (
                    var[0] != "_" or add_action_vars
                ):  # and var != "filled_in":
                    self.hidden_field(var, self.request.get_str_input(var))

    def hidden_field(
        self,
        var: str,
        value: HTMLTagValue,
        id_: str | None = None,
        add_var: bool = False,
        class_: CSSSpec | None = None,
    ) -> None:
        self.write_html(
            self.render_hidden_field(var=var, value=value, id_=id_, add_var=add_var, class_=class_)
        )

    def render_hidden_field(
        self,
        var: str,
        value: HTMLTagValue,
        id_: str | None = None,
        add_var: bool = False,
        class_: CSSSpec | None = None,
    ) -> HTML:
        if value is None:
            return HTML.empty()
        if add_var:
            self.add_form_var(var)
        return self.render_input(
            name=var,
            type_="hidden",
            id_=id_,
            value=value,
            class_=class_,
            autocomplete="off",
        )

    def do_actions(self) -> bool:
        return self.request.var("_do_actions") not in ["", None, _("No")]

    # Check if the given form is currently filled in (i.e. we display
    # the form a second time while showing value typed in at the first
    # time and complaining about invalid user input)
    def form_submitted(self, form_name: str | None = None) -> bool:
        if form_name is None:
            return self.request.has_var("filled_in")
        return self.request.var("filled_in") == form_name

    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname: str) -> bool | None:
        if self.request.has_var(varname):
            return bool(self.request.var(varname))
        if self.form_submitted(self.form_name):
            return False  # Form filled in but variable missing -> Checkbox not checked
        return None

    def button(
        self,
        varname: str,
        title: str,
        cssclass: str | None = None,
        style: str | None = None,
        help_: str | None = None,
        form: str | None = None,
        formnovalidate: bool = False,
    ) -> None:
        self.write_html(
            self.render_button(
                varname,
                title,
                cssclass,
                style,
                help_=help_,
                form=form,
                formnovalidate=formnovalidate,
            )
        )

    def render_button(
        self,
        varname: str,
        title: str,
        cssclass: str | None = None,
        style: str | None = None,
        help_: str | None = None,
        form: str | None = None,
        formnovalidate: bool = False,
    ) -> HTML:
        self.add_form_var(varname)
        return self.render_input(
            name=varname,
            type_="submit",
            id_=varname,
            class_=["button"] + ([cssclass] if cssclass else []),
            value=title,
            title=help_,
            style=style,
            form=form,
            formnovalidate="" if formnovalidate else None,
        )

    def buttonlink(
        self,
        href: str,
        text: str,
        add_transid: bool = False,
        obj_id: str | None = None,
        style: str | None = None,
        title: str | None = None,
        disabled: str | None = None,
        class_: CSSSpec | None = None,
    ) -> None:
        if add_transid:
            href += "&_transid=%s" % transactions.get()

        if not obj_id:
            obj_id = utils.gen_id()

        # Same API as other elements: class_ can be a list or string/None
        css_classes = ["button", "buttonlink"]
        if class_:
            if not isinstance(class_, list):
                css_classes.append(class_)
            else:
                css_classes.extend(class_)

        self.input(
            name=obj_id,
            type_="button",
            id_=obj_id,
            class_=css_classes,
            value=text,
            style=style,
            title=title,
            disabled=disabled,
            onclick="location.href=%s" % json.dumps(href),
        )

    def empty_icon_button(self) -> None:
        self._write(HTMLGenerator.render_icon("trans", cssclass="iconbutton trans"))

    def disabled_icon_button(self, icon: str) -> None:
        self._write(HTMLGenerator.render_icon(icon, cssclass="iconbutton"))

    # TODO: Cleanup to use standard attributes etc.
    def jsbutton(
        self,
        varname: str,
        text: str,
        onclick: str,
        style: str = "",
        cssclass: str | None = None,
        title: str = "",
        disabled: bool = False,
        class_: CSSSpec | None = None,
    ) -> None:
        classes = (
            ["button"]
            + ([] if cssclass is None else [cssclass])
            + ([] if class_ is None else class_)
        )

        if disabled:
            classes.append("disabled")
            disabled_arg: str | None = ""
        else:
            disabled_arg = None

        # autocomplete="off": Is needed for firefox not to set "disabled="disabled" during page reload
        # when it has been set on a page via javascript before. Needed for Setup activate changes page.
        self.input(
            name=varname,
            type_="button",
            id_=varname,
            class_=classes,
            autocomplete="off",
            onclick=onclick,
            style=style,
            disabled=disabled_arg,
            value=text,
            title=title,
        )

    def user_error(self, e: MKUserError, show_as_warning: bool = False) -> None:
        """Display the given MKUserError and store message for later use"""
        if show_as_warning:
            self.show_warning(str(e))
        else:
            self.show_error(str(e))
        user_errors.add(e)

    def show_user_errors(self) -> None:
        """Show all previously created user errors"""
        if user_errors:
            self.write_html(self.render_user_errors())

    def render_user_errors(self) -> HTML:
        """Render all previously created user errors"""
        return self.render_error(
            HTMLWriter.render_br().join(
                escaping.escape_to_html_permissive(s, escape_links=False)
                for s in user_errors.values()
            )
        )

    # TODO: Try and thin out this method's list of parameters - remove unused ones
    def text_input(
        self,
        varname: str,
        default_value: str = "",
        cssclass: str = "text",
        size: None | str | int = None,
        label: str | None = None,
        id_: str | None = None,
        submit: str | None = None,
        try_max_width: bool = False,
        read_only: bool = False,
        autocomplete: str | None = None,
        style: str | None = None,
        type_: str | None = None,
        oninput: str | None = None,
        onblur: str | None = None,
        placeholder: str | None = None,
        data_attrs: HTMLTagAttributes | None = None,
        required: bool = False,
        title: str | None = None,
    ) -> None:
        # Model
        error = user_errors.get(varname)
        value = self.request.get_str_input(varname, default_value)
        if not value:
            value = ""
        if error:
            self.set_focus(varname)
        self.form_vars.append(varname)

        if data_attrs is not None:
            assert all(data_attr_key.startswith("data-") for data_attr_key in data_attrs.keys())

        # View
        # TODO: Move styling away from py code
        # Until we get there: Try to simplify these width stylings and put them in a helper function
        # that's shared by text_input and text_area
        style_size: list[str] = []
        field_size: str | None = None

        if size is not None:
            if try_max_width:
                assert isinstance(size, int)
                style_size = ["min-width: %d.8ex;" % size]
                cssclass += " try_max_width"
            elif size == "max":
                style_size = ["width: 100%;"]
            else:
                assert isinstance(size, int)
                field_size = "%d" % (size + 1)
                if (style is None or "width:" not in style) and not self.mobile:
                    style_size = ["width: %d.8ex;" % size]

        attributes: HTMLTagAttributes = {
            "class": cssclass,
            "id": ("ti_%s" % varname) if (submit or label) and not id_ else id_,
            "style": style_size + ([] if style is None else [style]),
            "size": field_size,
            "autocomplete": autocomplete,
            "readonly": "true" if read_only else None,
            "value": value,
            "onblur": onblur,
            "oninput": oninput,
            "onkeydown": (
                ("cmk.forms.textinput_enter_submit(event, %s);" % json.dumps(submit))
                if submit
                else None
            ),
            "placeholder": placeholder,
            "required": "" if required else None,
            "title": title,
            **(data_attrs or {}),
        }

        if error:
            self.open_x(class_="inputerror")

        if label:
            assert id_ is not None
            self.label(label, for_=id_, class_="required" if required else None)

        input_type = "text" if type_ is None else type_
        assert isinstance(input_type, str)
        self.write_html(self.render_input(varname, type_=input_type, **attributes))

        if error:
            self.close_x()

    def status_label(
        self, content: HTMLContent, status: str, title: str, **attrs: HTMLTagAttributeValue
    ) -> None:
        """Shows a colored badge with text (used on Setup activation page for the site status)"""
        self.status_label_button(content, status, title, onclick=None, **attrs)

    def status_label_button(
        self,
        content: HTMLContent,
        status: str,
        title: str,
        onclick: str | None,
        **attrs: HTMLTagAttributeValue,
    ) -> None:
        """Shows a colored button with text (used in site and customer status snap-ins)"""
        self.div(
            content,
            title=title,
            class_=["status_label"] + (["button"] if onclick else []) + [status],
            onclick=onclick,
            **attrs,
        )

    def toggle_switch(
        self,
        enabled: bool,
        help_txt: str,
        class_: CSSSpec | None = None,
        href: str = "javascript:void(0)",
        onclick: str | None = None,
    ) -> None:
        class_ = [] if class_ is None else class_
        class_ += ["toggle_switch"]

        self.icon_button(
            url=href,
            title=help_txt,
            icon="toggle_" + ("on" if enabled else "off"),
            onclick=onclick,
            class_=class_,
        )

    def password_input(
        self,
        varname: str,
        default_value: str = "",
        cssclass: str = "text",
        size: None | str | int = None,
        label: str | None = None,
        id_: str | None = None,
        submit: str | None = None,
        try_max_width: bool = False,
        read_only: bool = False,
        autocomplete: str | None = None,
        placeholder: str | None = None,
    ) -> None:
        self.text_input(
            varname,
            default_value,
            cssclass=cssclass,
            size=size,
            label=label,
            id_=id_,
            submit=submit,
            type_="password",
            try_max_width=try_max_width,
            read_only=read_only,
            autocomplete=autocomplete,
            placeholder=placeholder,
        )

    def password_meter(self) -> None:
        """The call should be right behind the password_input call, since the
        meter looks for inputs in the same parent...

        Relies on the "zxcvbn-ts" package utilized within the
        "js/password_meter.ts" module"""
        # the class_name must be in sync with password_meter.ts
        class_name = "password_meter"
        # <label>
        self.write_html(render_start_tag(tag_name="label", close_tag=False))
        self.write_text_permissive(str(_("Strength:")))
        # <meter>
        self.write_html(
            render_start_tag(
                tag_name="meter",
                close_tag=False,
                max="5",
                class_=class_name,
                data_password_strength_1=_("Very Weak"),
                data_password_strength_2=_("Weak"),
                data_password_strength_3=_("Medium"),
                data_password_strength_4=_("Good"),
                data_password_strength_5=_("Strong"),
            )
        )
        # </meter>
        self.write_html(render_end_tag("meter"))
        # </label>
        self.write_html(render_end_tag("label"))

    def text_area(
        self,
        varname: str,
        deflt: str = "",
        rows: int = 4,
        cols: int = 30,
        try_max_width: bool = False,
        **attrs: HTMLTagAttributeValue,
    ) -> None:
        value = self.request.get_str_input(varname, deflt)
        error = user_errors.get(varname)

        self.form_vars.append(varname)
        if error:
            self.set_focus(varname)

        if try_max_width:
            style = "min-width: %d.8ex;" % cols
            cssclass = "try_max_width"

            if "class" in attrs:
                if isinstance(attrs["class"], list):
                    cssclass = " ".join([cssclass, *attrs["class"]])
                elif isinstance(attrs["class"], str):
                    cssclass += " " + attrs["class"]
            attrs["class"] = cssclass
        else:
            style = "width: %d.8ex;" % cols

        attrs["style"] = style
        attrs["rows"] = str(rows)
        attrs["cols"] = str(cols)
        attrs["name"] = varname

        # Fix handling of leading newlines (https://www.w3.org/TR/html5/syntax.html#element-restrictions)
        #
        # """
        # A single newline may be placed immediately after the start tag of pre
        # and textarea elements. This does not affect the processing of the
        # element. The otherwise optional newline must be included if the
        # element’s contents themselves start with a newline (because otherwise
        # the leading newline in the contents would be treated like the
        # optional newline, and ignored).
        # """
        if value and value.startswith("\n"):
            value = "\n" + value

        if error:
            self.open_x(class_="inputerror")
        self.write_html(render_element("textarea", value, **attrs))
        if error:
            self.close_x()

    # Choices is a list pairs of (key, title). They keys of the choices
    # and the default value must be of type None, str or unicode.
    def dropdown(
        self,
        varname: str,
        choices: Iterable[Choice] | Iterable[ChoiceGroup],
        locked_choice: ChoiceText | None = None,
        deflt: ChoiceId = "",
        ordered: bool = False,
        label: str | None = None,
        class_: CSSSpec | None = None,
        size: int = 1,
        read_only: bool = False,
        **attrs: HTMLTagAttributeValue,
    ) -> None:
        current = self.request.get_str_input(varname, deflt)
        error = user_errors.get(varname)
        if varname:
            self.form_vars.append(varname)

        # Normalize all choices to grouped choice structure
        grouped: GroupedChoices = []
        ungrouped_group = ChoiceGroup(title="", choices=[])
        grouped.append(ungrouped_group)
        for e in choices:
            if not isinstance(e, ChoiceGroup):
                ungrouped_group.choices.append(e)
            else:
                grouped.append(e)

        if error:
            self.open_x(class_="inputerror")

        if read_only:
            attrs["disabled"] = "disabled"
            self.hidden_field(varname, current, add_var=False)

        if label:
            self.label(label, for_=varname)

        # Do not enable select2 for select fields that allow multiple
        # selections like the dual list choice valuespec
        css_classes = (
            []
            if "multiple" in attrs or (isinstance(class_, list) and "ajax-vals" in class_)
            else ["select2-enable"]
        )

        if isinstance(class_, list):
            css_classes.extend(class_)
        elif class_ is not None:
            css_classes.append(class_)

        self.open_select(
            name=varname, id_=varname, label=label, class_=css_classes, size=str(size), **attrs
        )

        for group in grouped:
            if group.title:
                self.open_optgroup(label=group.title)

            for value, text in (
                group.choices if not ordered else sorted(group.choices, key=lambda a: a[1].lower())
            ):
                # if both the default in choices and current was '' then selected depended on the order in choices
                selected = (value == current) or (not value and not current)
                self.option(
                    text,
                    value=value if value else "",
                    selected="" if selected else None,
                )

            if locked_choice:
                self.option(locked_choice, value="", disabled="")

            if group.title:
                self.close_optgroup()

        self.close_select()
        if error:
            self.close_x()

    def icon_dropdown(
        self, varname: str, choices: Sequence[tuple[str, str, str]], deflt: str = ""
    ) -> None:
        current = self.request.var(varname, deflt)
        if varname:
            self.form_vars.append(varname)

        self.open_select(class_="icon", name=varname, id_=varname, size="1")
        for value, text, icon in choices:
            # if both the default in choices and current was '' then selected depended on the order in choices
            selected = (value == current) or (not value and not current)
            self.option(
                text,
                value=value if value else "",
                selected="" if selected else None,
                style="background-image:url(%s);" % theme.url(f"images/icon_{icon}.png"),
            )
        self.close_select()

    def upload_file(self, varname: str) -> None:
        # We need this to upload files, other enctypes won't work.
        error = user_errors.get(varname)
        if error:
            self.open_x(class_="inputerror")
        self.input(name=varname, type_="file")
        if error:
            self.close_x()
        self.form_vars.append(varname)

    def begin_radio_group(self, horizontal: bool = False) -> None:
        if self.mobile:
            attrs = {"data-type": "horizontal" if horizontal else None, "data-role": "controlgroup"}
            self._write(render_start_tag("fieldset", close_tag=False, **attrs))

    def end_radio_group(self) -> None:
        if self.mobile:
            self._write(render_end_tag("fieldset"))

    def radiobutton(self, varname: str, value: str, checked: bool, label: str | None) -> None:
        self.form_vars.append(varname)

        if self.request.has_var(varname):
            checked = self.request.var(varname) == value

        id_ = f"rb_{varname}_{value}" if label else None
        self.open_span(class_="radiobutton_group")
        self.input(
            name=varname, type_="radio", value=value, checked="" if checked else None, id_=id_
        )
        if label and id_:
            self.label(label, for_=id_)
        self.close_span()

    def begin_checkbox_group(self, horizonal: bool = False) -> None:
        self.begin_radio_group(horizonal)

    def end_checkbox_group(self) -> None:
        self.end_radio_group()

    def checkbox(
        self,
        varname: str,
        deflt: bool = False,
        label: HTMLContent = "",
        id_: str | None = None,
        **add_attr: HTMLTagAttributeValue,
    ) -> None:
        self._write(self.render_checkbox(varname, deflt, label, id_, **add_attr))

    def render_checkbox(
        self,
        varname: str,
        deflt: bool = False,
        label: HTMLContent = "",
        id_: str | None = None,
        **add_attr: HTMLTagAttributeValue,
    ) -> HTML:
        # Problem with checkboxes: The browser will add the variable
        # only to the URL if the box is checked. So in order to detect
        # whether we should add the default value, we need to detect
        # if the form is printed for the first time. This is the
        # case if "filled_in" is not set.
        value = self.get_checkbox(varname)
        if value is None:  # form not yet filled in
            value = deflt

        error = user_errors.get(varname)
        if id_ is None:
            id_ = "cb_%s" % varname

        add_attr["id"] = id_
        add_attr["CHECKED"] = "" if value else None

        code = self.render_input(name=varname, type_="checkbox", **add_attr) + self.render_label(
            label, for_=id_
        )
        code = HTMLWriter.render_span(code, class_="checkbox")

        if error:
            code = HTMLWriter.render_x(code, class_="inputerror")

        self.form_vars.append(varname)
        return code

    def render_floating_option(
        self,
        name: str,
        height: str,
        title: str | None,
        renderer: Callable[[], None],
    ) -> None:
        self.open_div(class_=["floatfilter", height, name])
        self.div(title, class_=["legend"])
        self.open_div(class_=["content"])
        renderer()
        self.close_div()
        self.close_div()

    def render_input(self, name: str | None, type_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        if type_ == "submit":
            self.form_has_submit_button = True
        attrs["type_"] = type_
        attrs["name"] = name
        return render_start_tag("input", close_tag=True, **attrs)

    def input(self, name: str | None, type_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_input(name, type_, **attrs))

    def icon(
        self,
        icon: Icon,
        title: str | None = None,
        id_: str | None = None,
        cssclass: str | None = None,
        class_: CSSSpec | None = None,
    ) -> None:
        self.write_html(
            HTMLGenerator.render_icon(
                icon=icon,
                title=title,
                id_=id_,
                cssclass=cssclass,
                class_=[] if class_ is None else class_,
            )
        )

    def empty_icon(self) -> None:
        self.write_html(HTMLGenerator.render_icon("trans"))

    @staticmethod
    def render_icon(
        icon: Icon,
        title: str | None = None,
        id_: str | None = None,
        cssclass: str | None = None,
        class_: CSSSpec | None = None,
        *,
        # Temporary measure for not having to change all call-sites at once.
        # The first step was to only change call sites from painters.
        theme: Theme = theme,
    ) -> HTML:
        classes = ["icon"] + ([] if cssclass is None else [cssclass])
        if isinstance(class_, list):
            classes.extend(class_)
        elif class_ is not None:
            classes.append(class_)

        icon_name = icon["icon"] if isinstance(icon, dict) else icon
        if icon_name is None:
            icon_name = "empty"
        src = icon_name if "/" in icon_name else theme.detect_icon_path(icon_name, prefix="icon_")
        if src.endswith(".png"):
            classes.append("png")
        if src.endswith("/icon_missing.svg") and title:
            title += " (%s)" % _("icon not found")

        icon_element = render_start_tag(
            "img",
            close_tag=True,
            title=title,
            id_=id_,
            class_=classes,
            src=src,
        )

        if isinstance(icon, dict) and icon["emblem"] is not None:
            return HTMLGenerator.render_emblem(icon["emblem"], title, id_, icon_element)

        return icon_element

    @staticmethod
    def render_emblem(
        emblem: str,
        title: str | None,
        id_: str | None,
        icon_element: HTML | None = None,
    ) -> HTML:
        """Render emblem to corresponding icon (icon_element in function call)
        or render emblem itself as icon image, used e.g. in view options."""

        emblem_path = theme.detect_icon_path(emblem, prefix="emblem_")
        if not icon_element:
            return render_start_tag(
                "img",
                close_tag=True,
                title=title,
                id_=id_,
                class_="icon",
                src=emblem_path,
            )

        return HTMLWriter.render_span(
            icon_element + HTMLWriter.render_img(emblem_path, class_="emblem"),
            class_="emblem",
        )

    @staticmethod
    def render_icon_button(
        url: None | str,
        title: str,
        icon: Icon,
        id_: str | None = None,
        onclick: HTMLTagAttributeValue | None = None,
        style: str | None = None,
        target: str | None = None,
        cssclass: str | None = None,
        class_: CSSSpec | None = None,
        # Temporary measure for not having to change all call-sites at once.
        # The first step was to only change call sites from painters.
        theme: Theme = theme,
    ) -> HTML:
        classes = [] if cssclass is None else [cssclass]
        if isinstance(class_, list):
            classes.extend(class_)
        elif class_ is not None:
            classes.append(class_)

        href = url if not onclick else "javascript:void(0)"
        assert href is not None

        return HTMLWriter.render_a(
            content=HTMLGenerator.render_icon(icon, cssclass="iconbutton", theme=theme),
            href=href,
            title=title,
            id_=id_,
            class_=classes,
            style=style,
            target=target if target else "",
            onfocus="if (this.blur) this.blur();",
            onclick=onclick,
        )

    def icon_button(
        self,
        url: str | None,
        title: str,
        icon: Icon,
        id_: str | None = None,
        onclick: HTMLTagAttributeValue | None = None,
        style: str | None = None,
        target: str | None = None,
        cssclass: str | None = None,
        class_: CSSSpec | None = None,
        # Temporary measure for not having to change all call-sites at once.
        # The first step was to only change call sites from painters.
        theme: Theme = theme,
    ) -> None:
        self.write_html(
            HTMLGenerator.render_icon_button(
                url, title, icon, id_, onclick, style, target, cssclass, class_, theme=theme
            )
        )

    def more_button(
        self, id_: str, dom_levels_up: int, additional_js: str = "", with_text: bool = False
    ) -> None:
        if user.show_mode == "enforce_show_more":
            return

        self.open_a(
            href="javascript:void(0)",
            id_="more_%s" % id_,
            class_=["more", "has_text" if with_text else ""],
            onfocus="if (this.blur) this.blur();",
            onclick="cmk.utils.toggle_more(this, %s, %d);%s"
            % (json.dumps(id_), dom_levels_up, additional_js),
        )
        self.open_div(title=_("Show more") if not with_text else "", class_="show_more")
        if with_text:
            self.write_text_permissive(_("show more"))
        self.close_div()
        self.open_div(title=_("Show less") if not with_text else "", class_="show_less")
        if with_text:
            self.write_text_permissive(_("show less"))
        self.close_div()
        self.close_a()

    def popup_trigger(
        self,
        content: HTML,
        ident: str,
        method: PopupMethod,
        data: Any = None,
        style: str | None = None,
        cssclass: CSSSpec | None = None,
        onclose: str | None = None,
        onopen: str | None = None,
        resizable: bool = False,
        popup_group: str | None = None,
        hover_switch_delay: int | None = None,
    ) -> None:
        self.write_html(
            HTMLGenerator.render_popup_trigger(
                content,
                ident,
                method,
                data,
                style,
                cssclass,
                onclose,
                onopen,
                resizable,
                popup_group,
                hover_switch_delay,
            )
        )

    @staticmethod
    def render_popup_trigger(
        content: HTML,
        ident: str,
        method: PopupMethod,
        data: Any = None,
        style: str | None = None,
        cssclass: CSSSpec | None = None,
        onclose: str | None = None,
        onopen: str | None = None,
        resizable: bool = False,
        popup_group: str | None = None,
        hover_switch_delay: int | None = None,
    ) -> HTML:
        onclick = "cmk.popup_menu.toggle_popup(event, this, {}, {}, {}, {}, {},  {});".format(
            json.dumps(ident),
            json.dumps(method.asdict()),
            json.dumps(data if data else None),
            json.dumps(onclose.replace("'", "\\'") if onclose else None),
            json.dumps(onopen.replace("'", "\\'") if onopen else None),
            json.dumps(resizable),
        )

        if popup_group:
            onmouseenter: str | None = (
                f"cmk.popup_menu.switch_popup_menu_group(this, {json.dumps(popup_group)}, {json.dumps(hover_switch_delay)})"
            )
            onmouseleave: str | None = "cmk.popup_menu.stop_popup_menu_group_switch(this)"
        else:
            onmouseenter = None
            onmouseleave = None

        atag = HTMLWriter.render_a(
            content,
            class_="popup_trigger",
            href="javascript:void(0);",
            # Needed to prevent wrong linking when views are parts of dashlets
            target="_self",
            onclick=onclick,
            onmouseenter=onmouseenter,
            onmouseleave=onmouseleave,
        )

        classes = ["popup_trigger"]
        if isinstance(cssclass, list):
            classes.extend(cssclass)
        elif cssclass:
            classes.append(cssclass)

        # TODO: Make method.content return HTML
        return HTMLWriter.render_div(
            atag + HTML.without_escaping(method.content),
            class_=classes,
            id_="popup_trigger_%s" % ident,
            style=style,
        )

    def element_dragger_url(self, dragging_tag: str, base_url: str) -> None:
        self.write_html(
            HTMLGenerator.render_element_dragger(
                dragging_tag,
                drop_handler="function(index){return cmk.element_dragging.url_drop_handler(%s, index);})"
                % json.dumps(base_url),
            )
        )

    def element_dragger_js(
        self, dragging_tag: str, drop_handler: str, handler_args: Mapping[str, Any]
    ) -> None:
        self.write_html(
            HTMLGenerator.render_element_dragger(
                dragging_tag,
                drop_handler=f"function(new_index){{return {drop_handler}({json.dumps(handler_args)}, new_index);}})",
            )
        )

    # Currently only tested with tables. But with some small changes it may work with other
    # structures too.
    @staticmethod
    def render_element_dragger(dragging_tag: str, drop_handler: str) -> HTML:
        return HTMLWriter.render_a(
            HTMLGenerator.render_icon("drag", _("Move this entry")),
            href="javascript:void(0)",
            class_=["element_dragger"],
            onmousedown=f"cmk.element_dragging.start(event, this, {json.dumps(dragging_tag.upper())}, {drop_handler}",
        )

    def date(
        self,
        var: str,
        value: str,
        id_: str,
        onchange: str | None = None,
    ) -> None:
        self.write_html(
            self.render_input(
                name=var,
                value=value,
                type_="date",
                id=id_,
                onchange=onchange,
            )
        )

    def time(
        self,
        var: str,
        value: str,
        id_: str,
        onchange: str | None = None,
    ) -> None:
        self.write_html(
            self.render_input(
                name=var,
                value=value,
                type_="time",
                id=id_,
                onchange=onchange,
            )
        )


html = request_local_attr("html", HTMLGenerator)
