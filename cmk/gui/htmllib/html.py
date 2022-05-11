#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import pprint
import re
from pathlib import Path
from typing import Any, Callable, cast, Dict, Iterable, List, Optional, Set, Tuple, Union

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.log as log
import cmk.gui.utils as utils
import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.top_heading import top_heading
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import enable_page_menu_entry, PageMenu
from cmk.gui.page_state import PageState
from cmk.gui.type_defs import (
    Choice,
    ChoiceGroup,
    ChoiceId,
    ChoiceText,
    CSSSpec,
    GroupedChoices,
    Icon,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.popups import PopupMethod
from cmk.gui.utils.theme import theme
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
        self._default_javascripts = ["main"]
        self.have_help = False

        # browser options
        self.browser_redirect = ""

        # Forms
        self.form_name: Optional[str] = None
        self.form_vars: List[str] = []
        self.form_has_submit_button: bool = False

        self.request = request

    @property
    def screenshotmode(self) -> bool:
        """Enabling the screenshot mode omits the fancy background and makes it white instead."""
        return bool(self.request.var("screenshotmode", "1" if active_config.screenshotmode else ""))

    def is_api_call(self) -> bool:
        return self.output_format != "html"

    def set_focus(self, varname: str) -> None:
        self.final_javascript(
            "cmk.utils.set_focus_by_name(%s, %s)"
            % (json.dumps(self.form_name), json.dumps(varname))
        )

    def set_focus_by_id(self, dom_id: str) -> None:
        self.final_javascript("cmk.utils.set_focus_by_id(%s)" % (json.dumps(dom_id)))

    def clear_default_javascript(self) -> None:
        del self._default_javascripts[:]

    def add_default_javascript(self, name: str) -> None:
        if name not in self._default_javascripts:
            self._default_javascripts.append(name)

    def immediate_browser_redirect(self, secs: float, url: str) -> None:
        self.javascript("cmk.utils.set_reload(%s, '%s');" % (secs, url))

    def add_body_css_class(self, cls: str) -> None:
        self._body_classes.append(cls)

    def reload_whole_page(self, url: Optional[str] = None) -> None:
        if not self.request.has_var("_ajaxid"):
            return self.final_javascript("cmk.utils.reload_whole_page(%s)" % json.dumps(url))
        return None

    def show_localization_hint(self) -> None:
        url = "wato.py?mode=edit_configvar&varname=user_localizations"
        self.write(
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

    def help(self, text: Union[None, HTML, str]) -> None:
        """Embed help box, whose visibility is controlled by a global button in the page.

        You may add macros like this to the help texts to create links to the user
        manual: [piggyback|Piggyback chapter].
        All such documentation references must be added to or included in the class DocReference.
        """
        self.write_html(self.render_help(text))

    def render_help(self, text: Union[None, HTML, str]) -> HTML:
        if isinstance(text, str):
            text = escaping.escape_text(text)
        elif isinstance(text, HTML):
            text = "%s" % text

        if not text:
            return HTML("")

        stripped = text.strip()
        if not stripped:
            return HTML("")

        help_text = HTMLGenerator.resolve_help_text_macros(stripped)

        self.enable_help_toggle()
        style = "display:%s;" % ("block" if user.show_help else "none")
        return HTMLWriter.render_div(HTML(help_text), class_="help", style=style)

    @staticmethod
    def resolve_help_text_macros(text: str) -> str:
        # text = ".*[<page_name>#<anchor_name>|<link_title>].*"
        # e.g. text = "[intro_setup#install|Welcome]" returns
        #      <a href="https://docs.checkmk.com/master/en/intro_setup.html#install">Welcome</a>
        urls: List[Optional[str]] = []
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
                text = text.replace(
                    match[0], '<a href="%s" target="_blank">%s</a>' % (urls[n], match[2])
                )
        return text

    def enable_help_toggle(self) -> None:
        self.have_help = True

    def debug(self, *x: Any) -> None:
        for element in x:
            try:
                formatted = pprint.pformat(element)
            except UnicodeDecodeError:
                formatted = repr(element)
            self.write(HTMLWriter.render_pre(formatted))

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

    def _head(self, title: str, javascripts: Optional[List[str]] = None) -> None:
        javascripts = javascripts if javascripts else []

        self.open_head()

        self.default_html_headers()
        self.title(title)

        # If the variable _link_target is set, then all links in this page
        # should be targetted to the HTML frame named by _link_target. This
        # is e.g. useful in the dash-board
        if self.link_target:
            self.base(target=self.link_target)

        fname = HTMLGenerator._css_filename_for_browser(theme.url("theme"))
        if fname is not None:
            self.stylesheet(fname)

        self._add_custom_style_sheet()

        # Load all scripts
        for js in self._default_javascripts + javascripts:
            filename_for_browser = HTMLGenerator.javascript_filename_for_browser(js)
            if filename_for_browser:
                self.javascript_file(filename_for_browser)

        if self.browser_reload != 0.0:
            if self.browser_redirect != "":
                self.javascript(
                    "cmk.utils.set_reload(%s, '%s')" % (self.browser_reload, self.browser_redirect)
                )
            else:
                self.javascript("cmk.utils.set_reload(%s)" % (self.browser_reload))

        self.close_head()

    def _add_custom_style_sheet(self) -> None:
        for css in HTMLGenerator._plugin_stylesheets():
            self.write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)

        if active_config.custom_style_sheet:
            self.write(
                '<link rel="stylesheet" type="text/css" href="%s">\n'
                % active_config.custom_style_sheet
            )

    @staticmethod
    def _plugin_stylesheets() -> Set[str]:
        plugin_stylesheets = set([])
        for directory in [
            Path(cmk.utils.paths.web_dir, "htdocs", "css"),
            cmk.utils.paths.local_web_dir / "htdocs" / "css",
        ]:
            if directory.exists():
                for entry in directory.iterdir():
                    if entry.suffix == ".css":
                        plugin_stylesheets.add(entry.name)
        return plugin_stylesheets

    # Make the browser load specified javascript files. We have some special handling here:
    # a) files which can not be found shal not be loaded
    # b) in OMD environments, add the Checkmk version to the version (prevents update problems)
    # c) load the minified javascript when not in debug mode
    @staticmethod
    def javascript_filename_for_browser(jsname: str) -> Optional[str]:
        filename_for_browser = None
        rel_path = "share/check_mk/web/htdocs/js"
        if active_config.debug:
            min_parts = ["", "_min"]
        else:
            min_parts = ["_min", ""]

        for min_part in min_parts:
            fname = f"{jsname}{min_part}.js"
            if (cmk.utils.paths.omd_root / rel_path / fname).exists() or (
                cmk.utils.paths.omd_root / "local" / rel_path / fname
            ).exists():
                filename_for_browser = f"js/{jsname}{min_part}-{cmk_version.__version__}.js"
                break

        return filename_for_browser

    @staticmethod
    def _css_filename_for_browser(css: str) -> Optional[str]:
        rel_path = f"share/check_mk/web/htdocs/{css}.css"
        if (cmk.utils.paths.omd_root / rel_path).exists() or (
            cmk.utils.paths.omd_root / "local" / rel_path
        ).exists():
            return f"{css}-{cmk_version.__version__}.css"
        return None

    def html_head(
        self, title: str, javascripts: Optional[List[str]] = None, force: bool = False
    ) -> None:
        if force or not self._header_sent:
            self.write_html(HTML("<!DOCTYPE HTML>\n"))
            self.open_html()
            self._head(title, javascripts)
            self._header_sent = True

    def header(
        self,
        title: str,
        breadcrumb: Breadcrumb,
        page_menu: Optional[PageMenu] = None,
        page_state: Optional[PageState] = None,
        javascripts: Optional[List[str]] = None,
        force: bool = False,
        show_body_start: bool = True,
        show_top_heading: bool = True,
    ) -> None:
        if self.output_format != "html":
            return

        if not self._header_sent:
            if show_body_start:
                self.body_start(title, javascripts=javascripts, force=force)

            self._header_sent = True

            breadcrumb = breadcrumb or Breadcrumb()

            if self.render_headfoot and show_top_heading:
                top_heading(
                    self,
                    self.request,
                    title,
                    breadcrumb=breadcrumb,
                    page_menu=page_menu or PageMenu(breadcrumb=breadcrumb),
                    page_state=page_state,
                    browser_reload=self.browser_reload,
                )
        self.begin_page_content()

    def body_start(
        self, title: str = "", javascripts: Optional[List[str]] = None, force: bool = False
    ) -> None:
        self.html_head(title, javascripts, force)
        self.open_body(class_=self._get_body_css_classes(), data_theme=theme.get())

    def _get_body_css_classes(self) -> List[str]:
        classes = self._body_classes[:]
        if self.screenshotmode:
            classes += ["screenshotmode"]
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
            enable_page_menu_entry("inline_help")
        self.write_final_javascript()
        self.javascript("cmk.visibility_detection.initialize();")
        self.close_body()
        self.close_html()

    def begin_form(
        self,
        name: str,
        action: Optional[str] = None,
        method: str = "GET",
        onsubmit: Optional[str] = None,
        add_transid: bool = True,
    ) -> None:
        self.form_name = name
        self.form_vars = []
        self.form_has_submit_button = False

        if action is None:
            action = requested_file_name(self.request) + ".py"
        self.open_form(
            id_="form_%s" % name,
            name=name,
            class_=name,
            action=action,
            method=method,
            onsubmit=onsubmit,
            enctype="multipart/form-data" if method.lower() == "post" else None,
        )
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

    def add_confirm_on_submit(self, form_name: str, msg: str) -> None:
        """Adds a confirm dialog to a form that is shown before executing a form submission"""
        self.javascript(
            "cmk.forms.add_confirm_on_submit(%s, %s)"
            % (json.dumps("form_%s" % form_name), json.dumps(escaping.escape_text(msg)))
        )

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
        self, varlist: Optional[List[str]] = None, add_action_vars: bool = False
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
        id_: Optional[str] = None,
        add_var: bool = False,
        class_: CSSSpec = None,
    ) -> None:
        self.write_html(
            self.render_hidden_field(var=var, value=value, id_=id_, add_var=add_var, class_=class_)
        )

    def render_hidden_field(
        self,
        var: str,
        value: HTMLTagValue,
        id_: Optional[str] = None,
        add_var: bool = False,
        class_: CSSSpec = None,
    ) -> HTML:
        if value is None:
            return HTML("")
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
    def form_submitted(self, form_name: Optional[str] = None) -> bool:
        if form_name is None:
            return self.request.has_var("filled_in")
        return self.request.var("filled_in") == form_name

    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname: str) -> Optional[bool]:
        if self.request.has_var(varname):
            return bool(self.request.var(varname))
        if self.form_submitted(self.form_name):
            return False  # Form filled in but variable missing -> Checkbox not checked
        return None

    def button(
        self,
        varname: str,
        title: str,
        cssclass: Optional[str] = None,
        style: Optional[str] = None,
        help_: Optional[str] = None,
        form: Optional[str] = None,
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
        cssclass: Optional[str] = None,
        style: Optional[str] = None,
        help_: Optional[str] = None,
        form: Optional[str] = None,
        formnovalidate: bool = False,
    ) -> HTML:
        self.add_form_var(varname)
        return self.render_input(
            name=varname,
            type_="submit",
            id_=varname,
            class_=["button", cssclass if cssclass else None],
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
        obj_id: Optional[str] = None,
        style: Optional[str] = None,
        title: Optional[str] = None,
        disabled: Optional[str] = None,
        class_: CSSSpec = None,
    ) -> None:
        if add_transid:
            href += "&_transid=%s" % transactions.get()

        if not obj_id:
            obj_id = utils.gen_id()

        # Same API as other elements: class_ can be a list or string/None
        css_classes: List[Optional[str]] = ["button", "buttonlink"]
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
        self.write(HTMLGenerator.render_icon("trans", cssclass="iconbutton trans"))

    def disabled_icon_button(self, icon: str) -> None:
        self.write(HTMLGenerator.render_icon(icon, cssclass="iconbutton"))

    # TODO: Cleanup to use standard attributes etc.
    def jsbutton(
        self,
        varname: str,
        text: str,
        onclick: str,
        style: str = "",
        cssclass: Optional[str] = None,
        title: str = "",
        disabled: bool = False,
        class_: CSSSpec = None,
    ) -> None:
        if not isinstance(class_, list):
            class_ = [class_]
        # TODO: Investigate why mypy complains about the latest argument
        classes = ["button", cssclass] + cast(List[Optional[str]], class_)

        if disabled:
            class_.append("disabled")
            disabled_arg: Optional[str] = ""
        else:
            disabled_arg = None

        # autocomplete="off": Is needed for firefox not to set "disabled="disabled" during page reload
        # when it has been set on a page via javascript before. Needed for WATO activate changes page.
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

    def user_error(self, e: MKUserError) -> None:
        """Display the given MKUserError and store message for later use"""
        self.show_error(str(e))
        user_errors.add(e)

    def show_user_errors(self) -> None:
        """Show all previously created user errors"""
        if user_errors:
            self.show_error(
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
        size: Union[None, str, int] = None,
        label: Optional[str] = None,
        id_: Optional[str] = None,
        submit: Optional[str] = None,
        try_max_width: bool = False,
        read_only: bool = False,
        autocomplete: Optional[str] = None,
        style: Optional[str] = None,
        type_: Optional[str] = None,
        onkeyup: Optional[str] = None,
        onblur: Optional[str] = None,
        placeholder: Optional[str] = None,
        data_world: Optional[str] = None,
        data_max_labels: Optional[int] = None,
        required: bool = False,
        title: Optional[str] = None,
    ) -> None:

        # Model
        error = user_errors.get(varname)
        value = self.request.get_str_input(varname, default_value)
        if not value:
            value = ""
        if error:
            self.set_focus(varname)
        self.form_vars.append(varname)

        # View
        # TODO: Move styling away from py code
        # Until we get there: Try to simplify these width stylings and put them in a helper function
        # that's shared by text_input and text_area
        style_size: Optional[str] = None
        field_size: Optional[str] = None

        if size is not None:
            if try_max_width:
                assert isinstance(size, int)
                style_size = "min-width: %d.8ex;" % size
                cssclass += " try_max_width"
            else:
                if size == "max":
                    style_size = "width: 100%;"
                else:
                    assert isinstance(size, int)
                    field_size = "%d" % (size + 1)
                    if (style is None or "width:" not in style) and not self.mobile:
                        style_size = "width: %d.8ex;" % size

        attributes: HTMLTagAttributes = {
            "class": cssclass,
            "id": ("ti_%s" % varname) if (submit or label) and not id_ else id_,
            "style": [style_size] + ([] if style is None else [style]),
            "size": field_size,
            "autocomplete": autocomplete,
            "readonly": "true" if read_only else None,
            "value": value,
            "onblur": onblur,
            "onkeyup": onkeyup,
            "onkeydown": ("cmk.forms.textinput_enter_submit(event, %s);" % json.dumps(submit))
            if submit
            else None,
            "placeholder": placeholder,
            "data-world": data_world,
            "data-max-labels": None if data_max_labels is None else str(data_max_labels),
            "required": "" if required else None,
            "title": title,
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
        """Shows a colored badge with text (used on WATO activation page for the site status)"""
        self.status_label_button(content, status, title, onclick=None, **attrs)

    def status_label_button(
        self,
        content: HTMLContent,
        status: str,
        title: str,
        onclick: Optional[str],
        **attrs: HTMLTagAttributeValue,
    ) -> None:
        """Shows a colored button with text (used in site and customer status snapins)"""
        button_cls = "button" if onclick else None
        self.div(
            content,
            title=title,
            class_=["status_label", button_cls, status],
            onclick=onclick,
            **attrs,
        )

    def toggle_switch(
        self,
        enabled: bool,
        help_txt: str,
        class_: CSSSpec = None,
        href: str = "javascript:void(0)",
        **attrs: HTMLTagAttributeValue,
    ) -> None:
        # Same API as other elements: class_ can be a list or string/None
        if not isinstance(class_, list):
            class_ = [class_]

        class_ += [
            "toggle_switch",
            "on" if enabled else "off",
        ]
        onclick = attrs.pop("onclick", None)

        self.open_div(class_=class_, **attrs)
        self.a(
            content=_("on") if enabled else _("off"),
            href=href,
            title=help_txt,
            onclick=onclick,
        )
        self.close_div()

    def password_input(
        self,
        varname: str,
        default_value: str = "",
        cssclass: str = "text",
        size: Union[None, str, int] = None,
        label: Optional[str] = None,
        id_: Optional[str] = None,
        submit: Optional[str] = None,
        try_max_width: bool = False,
        read_only: bool = False,
        autocomplete: Optional[str] = None,
        placeholder: Optional[str] = None,
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
        choices: Union[Iterable[Choice], Iterable[ChoiceGroup]],
        locked_choice: Optional[ChoiceText] = None,
        deflt: ChoiceId = "",
        ordered: bool = False,
        label: Optional[str] = None,
        class_: CSSSpec = None,
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
        css_classes: List[Optional[str]] = ["select2-enable"]
        if "multiple" in attrs or (isinstance(class_, list) and "ajax-vals" in class_):
            css_classes = []

        if isinstance(class_, list):
            css_classes.extend(class_)
        else:
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
        self, varname: str, choices: List[Tuple[str, str, str]], deflt: str = ""
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
            self.write(render_start_tag("fieldset", close_tag=False, **attrs))

    def end_radio_group(self) -> None:
        if self.mobile:
            self.write(render_end_tag("fieldset"))

    def radiobutton(self, varname: str, value: str, checked: bool, label: Optional[str]) -> None:
        self.form_vars.append(varname)

        if self.request.has_var(varname):
            checked = self.request.var(varname) == value

        id_ = "rb_%s_%s" % (varname, value) if label else None
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
        id_: Optional[str] = None,
        **add_attr: HTMLTagAttributeValue,
    ) -> None:
        self.write(self.render_checkbox(varname, deflt, label, id_, **add_attr))

    def render_checkbox(
        self,
        varname: str,
        deflt: bool = False,
        label: HTMLContent = "",
        id_: Optional[str] = None,
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
        title: Optional[str],
        renderer: Callable[[], None],
    ) -> None:
        self.open_div(class_=["floatfilter", height, name])
        self.div(title, class_=["legend"])
        self.open_div(class_=["content"])
        renderer()
        self.close_div()
        self.close_div()

    def render_input(self, name: Optional[str], type_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        if type_ == "submit":
            self.form_has_submit_button = True
        attrs["type_"] = type_
        attrs["name"] = name
        return render_start_tag("input", close_tag=True, **attrs)

    def input(self, name: Optional[str], type_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_input(name, type_, **attrs))

    def icon(
        self,
        icon: Icon,
        title: Optional[str] = None,
        id_: Optional[str] = None,
        cssclass: Optional[str] = None,
        class_: CSSSpec = None,
    ) -> None:
        self.write_html(
            HTMLGenerator.render_icon(
                icon=icon, title=title, id_=id_, cssclass=cssclass, class_=class_
            )
        )

    def empty_icon(self) -> None:
        self.write_html(HTMLGenerator.render_icon("trans"))

    @staticmethod
    def render_icon(
        icon: Icon,
        title: Optional[str] = None,
        id_: Optional[str] = None,
        cssclass: Optional[str] = None,
        class_: CSSSpec = None,
    ) -> HTML:
        classes = ["icon", cssclass]
        if isinstance(class_, list):
            classes.extend(class_)
        else:
            classes.append(class_)

        icon_name = icon["icon"] if isinstance(icon, dict) else icon
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
        title: Optional[str],
        id_: Optional[str],
        icon_element: Optional[HTML] = None,
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
        url: Union[None, str, str],
        title: str,
        icon: Icon,
        id_: Optional[str] = None,
        onclick: Optional[HTMLTagAttributeValue] = None,
        style: Optional[str] = None,
        target: Optional[str] = None,
        cssclass: Optional[str] = None,
        class_: CSSSpec = None,
    ) -> HTML:
        # Same API as other elements: class_ can be a list or string/None
        classes = [cssclass]
        if isinstance(class_, list):
            classes.extend(class_)
        else:
            classes.append(class_)

        href = url if not onclick else "javascript:void(0)"
        assert href is not None

        return HTMLWriter.render_a(
            content=HTML(HTMLGenerator.render_icon(icon, cssclass="iconbutton")),
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
        url: Optional[str],
        title: str,
        icon: Icon,
        id_: Optional[str] = None,
        onclick: Optional[HTMLTagAttributeValue] = None,
        style: Optional[str] = None,
        target: Optional[str] = None,
        cssclass: Optional[str] = None,
        class_: CSSSpec = None,
    ) -> None:
        self.write_html(
            HTMLGenerator.render_icon_button(
                url, title, icon, id_, onclick, style, target, cssclass, class_
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
            self.write_text(_("show more"))
        self.close_div()
        self.open_div(title=_("Show less") if not with_text else "", class_="show_less")
        if with_text:
            self.write_text(_("show less"))
        self.close_div()
        self.close_a()

    def popup_trigger(
        self,
        content: HTML,
        ident: str,
        method: PopupMethod,
        data: Any = None,
        style: Optional[str] = None,
        cssclass: CSSSpec = None,
        onclose: Optional[str] = None,
        onopen: Optional[str] = None,
        resizable: bool = False,
        popup_group: Optional[str] = None,
        hover_switch_delay: Optional[int] = None,
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
        style: Optional[str] = None,
        cssclass: CSSSpec = None,
        onclose: Optional[str] = None,
        onopen: Optional[str] = None,
        resizable: bool = False,
        popup_group: Optional[str] = None,
        hover_switch_delay: Optional[int] = None,
    ) -> HTML:

        onclick = "cmk.popup_menu.toggle_popup(event, this, %s, %s, %s, %s, %s,  %s);" % (
            json.dumps(ident),
            json.dumps(method.asdict()),
            json.dumps(data if data else None),
            json.dumps(onclose.replace("'", "\\'") if onclose else None),
            json.dumps(onopen.replace("'", "\\'") if onopen else None),
            json.dumps(resizable),
        )

        if popup_group:
            onmouseenter: Optional[str] = "cmk.popup_menu.switch_popup_menu_group(this, %s, %s)" % (
                json.dumps(popup_group),
                json.dumps(hover_switch_delay),
            )
            onmouseleave: Optional[str] = "cmk.popup_menu.stop_popup_menu_group_switch(this)"
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

        classes: List[Optional[str]] = ["popup_trigger"]
        if isinstance(cssclass, list):
            classes.extend(cssclass)
        elif cssclass:
            classes.append(cssclass)

        # TODO: Make method.content return HTML
        return HTMLWriter.render_div(
            atag + HTML(method.content), class_=classes, id_="popup_trigger_%s" % ident, style=style
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
        self, dragging_tag: str, drop_handler: str, handler_args: Dict[str, Any]
    ) -> None:
        self.write_html(
            HTMLGenerator.render_element_dragger(
                dragging_tag,
                drop_handler="function(new_index){return %s(%s, new_index);})"
                % (drop_handler, json.dumps(handler_args)),
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
            onmousedown="cmk.element_dragging.start(event, this, %s, %s"
            % (json.dumps(dragging_tag.upper()), drop_handler),
        )
