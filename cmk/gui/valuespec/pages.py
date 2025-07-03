#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import socket
from collections.abc import Mapping, Sequence

import cmk.utils
import cmk.utils.paths
from cmk.utils.encryption import fetch_certificate_details

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageEndpoint, PageRegistry, PageResult
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel

from .definitions import HostAddress, IconSelector, ListOfMultiple, NetworkPort, ValueSpec


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_fetch_ca", AjaxFetchCA))
    page_registry.register(PageEndpoint("ajax_popup_icon_selector", ajax_popup_icon_selector))


def ajax_popup_icon_selector(config: Config) -> None:
    """AJAX API call for rendering the icon selector"""
    varprefix = request.get_ascii_input_mandatory("varprefix")
    value = request.var("value")
    allow_empty = request.var("allow_empty") == "1"
    show_builtin_icons = request.var("show_builtin_icons") == "1"

    vs = IconSelector(allow_empty=allow_empty, show_builtin_icons=show_builtin_icons)
    vs.render_popup_input(varprefix, value)


class ABCPageListOfMultipleGetChoice(AjaxPage, abc.ABC):
    @abc.abstractmethod
    def _get_choices(self, api_request: Mapping[str, str]) -> Sequence[tuple[str, ValueSpec]]:
        raise NotImplementedError()

    def page(self, config: Config) -> dict:
        api_request = request.get_request()
        vs = ListOfMultiple(
            choices=self._get_choices(api_request), choice_page_name="unused_dummy_page"
        )
        with output_funnel.plugged():
            vs.show_choice_row(api_request["varprefix"], api_request["ident"], {})
            return {"html_code": output_funnel.drain()}


class AjaxFetchCA(AjaxPage):
    def page(self, config: Config) -> PageResult:
        check_csrf_token()
        user.need_permission("general.server_side_requests")

        try:
            vs_address = HostAddress()
            address = vs_address.from_html_vars("address")
            vs_address.validate_value(address, "address")

            vs_port = NetworkPort(title=None)
            port = vs_port.from_html_vars("port")
            vs_port.validate_value(port, "port")
        except Exception:
            raise MKUserError(None, _("Please provide a valid host and port"))

        try:
            certs = fetch_certificate_details(
                cmk.utils.paths.trusted_ca_file, socket.AF_INET, (address, port)
            )
        except Exception as e:
            raise MKUserError(None, _("Error fetching data: %s") % e)

        for cert in certs:
            if not cert.is_ca:
                continue

            try:
                cert_pem = cert.verify_result.cert_pem.decode("ascii")
            except Exception:
                raise MKUserError(None, _("Failed to decode certificate data"))

            def row(key: str, value: str) -> HTML:
                return HTMLWriter.render_tr(
                    HTMLWriter.render_td(key) + HTMLWriter.render_td(value), class_="data"
                )

            summary = HTMLWriter.render_table(
                row(_("Issued to"), cert.issued_to)
                + row(_("Issued by"), cert.issued_by)
                + row(_("Valid from"), cert.valid_from)
                + row(_("Valid until"), cert.valid_till)
                + row(_("Fingerprint"), cert.digest_sha256),
                class_="data",
            )

            return {"summary": summary, "cert_pem": cert_pem}

        raise MKUserError(None, _("Found no CA"))
