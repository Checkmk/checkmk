#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import availability
from cmk.gui.availability import (
    AVAnnotationKey,
    AVAnnotations,
    AVObjectType,
    AVOptions,
    AVRawData,
)
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.table import table_element
from cmk.gui.top_heading import top_heading
from cmk.gui.type_defs import HTTPVariables, IconNames, StaticIcon
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri, urlencode_vars
from cmk.gui.valuespec import (
    AbsoluteDate,
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    HostState,
    MonitoringState,
    Optional,
    TextAreaUnicode,
    TextInput,
)
from cmk.utils import paths
from cmk.utils.servicename import ServiceName
from cmk.utils.statename import host_state_name, service_state_name


def show_annotations(
    annotations: AVAnnotations,
    av_rawdata: AVRawData,
    what: AVObjectType,
    avoptions: AVOptions,
    omit_service: bool,
) -> None:
    annos_to_render = availability.get_relevant_annotations(
        annotations, av_rawdata, what, avoptions
    )
    render_date = availability.get_annotation_date_render_function(annos_to_render, avoptions)

    with table_element(
        title=_("Annotations"), omit_if_empty=True, limit=active_config.table_row_limit
    ) as table:
        for nr, ((site_id, host, service), annotation) in enumerate(annos_to_render):
            table.row()
            table.cell("#", css=["narrow nowrap"])
            html.write_text_permissive(nr)
            table.cell("", css=["buttons"])
            anno_vars: HTTPVariables = [
                ("anno_site", site_id),
                ("anno_host", host),
                ("anno_service", service or ""),
                ("anno_from", int(annotation["from"])),
                ("anno_until", int(annotation["until"])),
            ]
            edit_url = makeuri(request, anno_vars)
            html.icon_button(edit_url, _("Edit this annotation"), StaticIcon(IconNames.edit))
            del_anno: HTTPVariables = [("_delete_annotation", "1")]
            delete_url = make_confirm_delete_link(
                url=makeactionuri(request, transactions, del_anno + anno_vars),
                title=_("Delete annotation #%d") % nr,
                message=_("Annotation: %s") % " ".join(annotation["text"].strip().split()),
            )
            html.icon_button(delete_url, _("Delete this annotation"), StaticIcon(IconNames.delete))

            if not omit_service:
                if "omit_host" not in avoptions["labelling"]:
                    host_url = "view.py?" + urlencode_vars(
                        [("view_name", "hoststatus"), ("site", site_id), ("host", host)]
                    )
                    table.cell(_("Host"), HTMLWriter.render_a(host, host_url))

                if what == "service":
                    if service:
                        service_url = "view.py?" + urlencode_vars(
                            [
                                ("view_name", "service"),
                                ("site", site_id),
                                ("host", host),
                                ("service", service),
                            ]
                        )
                        # TODO: honor use_display_name. But we have no display names here...
                        service_name = service
                        table.cell(_("Service"), HTMLWriter.render_a(service_name, service_url))
                    else:
                        table.cell(_("Service"), "")  # Host annotation in service table

            table.cell(_("From"), render_date(annotation["from"]), css=["nobr narrow"])
            table.cell(_("Until"), render_date(annotation["until"]), css=["nobr narrow"])
            table.cell("", css=["buttons"])
            if annotation.get("downtime") is True:
                html.static_icon(
                    StaticIcon(IconNames.downtime),
                    title=_("This period has been reclassified as a scheduled downtime"),
                )
            elif annotation.get("downtime") is False:
                html.static_icon(
                    StaticIcon(IconNames.nodowntime),
                    title=_("This period has been reclassified as not being a scheduled downtime"),
                )
            recl_host_state = annotation.get("host_state")
            if recl_host_state is not None:
                html.static_icon(
                    StaticIcon(IconNames.status),
                    title=_("This period has been reclassified in host state to state: %s")
                    % host_state_name(recl_host_state),
                )
            recl_svc_state = annotation.get("service_state")
            if recl_svc_state is not None:
                html.static_icon(
                    StaticIcon(IconNames.status),
                    title=_("This period has been reclassified in service state to state: %s")
                    % service_state_name(recl_svc_state),
                )

            table.cell(
                _("Annotation"), escape_to_html_permissive(annotation["text"], escape_links=False)
            )
            table.cell(_("Author"), annotation["author"])
            table.cell(_("Entry"), render_date(annotation["date"]), css=["nobr narrow"])
            if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.COMMUNITY:
                table.cell(
                    _("Hide in report"), _("Yes") if annotation.get("hide_from_report") else _("No")
                )


def _edit_annotation(breadcrumb: Breadcrumb, *, debug: bool) -> bool:
    (
        site_id,
        hostname,
        host_state,
        service,
        service_state,
        fromtime,
        untiltime,
        site_host_svc,
    ) = _handle_anno_request_vars()

    # Find existing annotation with this specification
    annotations = availability.load_annotations()
    annotation = availability.find_annotation(
        annotations, site_host_svc, host_state, service_state, fromtime, untiltime
    )

    if annotation:
        value = annotation.copy()
        value.setdefault("host_state", None)
        value.setdefault("service_state", None)
    else:
        value = {
            "host_state": None,
            "service_state": None,
            "from": fromtime,
            "until": untiltime,
            "text": "",
        }

    value["host"] = hostname
    value["service"] = service
    value["site"] = site_id

    if transactions.check_transaction():
        try:
            vs = _vs_annotation()
            value = vs.from_html_vars("_editanno")
            vs.validate_value(value, "_editanno")

            site_host_svc = (value["site"], value["host"], value["service"])
            del value["site"]
            del value["host"]
            value["date"] = time.time()
            value["author"] = user.id
            availability.update_annotations(site_host_svc, value, replace_existing=annotation)
            request.del_var("filled_in")
            return False
        except MKUserError as e:
            html.user_error(e)

    title = _("Edit annotation of ") + hostname
    if service:
        title += "/" + service

    html.body_start(
        title,
        lang=user.language,
        inject_js_profiling_code=active_config.inject_js_profiling_code,
        load_frontend_vue=active_config.load_frontend_vue,
        custom_style_sheet=active_config.custom_style_sheet,
        screenshotmode=active_config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
    )

    breadcrumb = _edit_annotation_breadcrumb(breadcrumb, title)
    top_heading(
        html,
        request,
        title,
        breadcrumb,
        _edit_annotation_page_menu(breadcrumb),
        browser_reload=html.browser_reload,
        debug=debug,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )

    with html.form_context("editanno", method="GET"):
        _vs_annotation().render_input_as_form("_editanno", value)
        html.hidden_fields()

    html.body_end()
    return True


def _edit_annotation_breadcrumb(breadcrumb: Breadcrumb, title: str) -> Breadcrumb:
    breadcrumb.append(
        BreadcrumbItem(
            title=title,
            url=makeuri(request, []),
        )
    )
    return breadcrumb


def _edit_annotation_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return make_simple_form_page_menu(
        _("Annotation"), breadcrumb, form_name="editanno", button_name="_save"
    )


def _validate_reclassify_of_states(value: dict[str, object], varprefix: str) -> None:
    host_state = value.get("host_state")
    if host_state is not None:
        if not value.get("host"):
            raise MKUserError(
                "_editanno_p_host", _("Please set a host name for host state reclassification")
            )

    service_state = value.get("service_state")
    if service_state is not None:
        if not value.get("service"):
            raise MKUserError(
                "_editanno_p_service_value",
                _("Please set a service name for service state reclassification"),
            )


def _vs_annotation() -> Dictionary:
    elements: list[DictionaryEntry] = [
        ("site", TextInput(title=_("Site"))),
        ("host", TextInput(title=_("Host name"))),
        (
            "host_state",
            Optional(
                valuespec=HostState(),
                sameline=True,
                title=_("Host state"),
                label=_("Reclassify host state of this period"),
            ),
        ),
        (
            "service",
            Optional(
                valuespec=TextInput(allow_empty=False),
                sameline=True,
                title=_("Service"),
                label=_("Service name"),
            ),
        ),
        (
            "service_state",
            Optional(
                valuespec=MonitoringState(),
                sameline=True,
                title=_("Service state"),
                label=_("Reclassify service state of this period"),
            ),
        ),
        ("from", AbsoluteDate(title=_("Start-Time"), include_time=True)),
        ("until", AbsoluteDate(title=_("End-Time"), include_time=True)),
        (
            "downtime",
            Optional(
                valuespec=DropdownChoice(
                    choices=[
                        (True, _("regard as scheduled downtime")),
                        (False, _("do not regard as scheduled downtime")),
                    ],
                ),
                title=_("Scheduled downtime"),
                label=_("Reclassify downtime of this period"),
            ),
        ),
        ("text", TextAreaUnicode(title=_("Annotation"), allow_empty=False)),
    ]
    extra_elements: list[DictionaryEntry] = (
        []
        if cmk_version.edition(paths.omd_root) is cmk_version.Edition.COMMUNITY
        else [("hide_from_report", Checkbox(title=_("Hide annotation in report")))]
    )
    return Dictionary(
        elements + extra_elements,
        title=_("Edit annotation"),
        optional_keys=[],
        validate=_validate_reclassify_of_states,
    )


# Called at the beginning of every availability page
def handle_delete_annotations() -> None:
    if request.var("_delete_annotation"):
        (
            _site_id,
            _hostname,
            _service,
            host_state,
            service_state,
            fromtime,
            untiltime,
            site_host_svc,
        ) = _handle_anno_request_vars()

        annotations = availability.load_annotations()
        annotation = availability.find_annotation(
            annotations, site_host_svc, host_state, service_state, fromtime, untiltime
        )
        if not annotation:
            return

        availability.delete_annotation(
            annotations, site_host_svc, host_state, service_state, fromtime, untiltime
        )
        availability.save_annotations(annotations)


def _handle_edit_annotations(breadcrumb: Breadcrumb, *, debug: bool) -> bool:
    # Avoid reshowing edit form after edit and reload
    if transactions.is_transaction() and not transactions.transaction_valid():
        return False
    if request.var("anno_host") and not request.var("_delete_annotation"):
        finished = _edit_annotation(breadcrumb, debug=debug)
    else:
        finished = False

    return finished


def _handle_anno_request_vars() -> tuple[
    str, str, str | None, str | None, str | None, float, float, AVAnnotationKey
]:
    site_id = request.var("anno_site") or ""
    hostname = request.get_str_input_mandatory("anno_host")
    host_state = request.var("anno_host_state") or None
    service = request.var("anno_service") or None
    service_state = request.var("anno_service_state") or None
    fromtime = request.get_float_input_mandatory("anno_from")
    untiltime = request.get_float_input_mandatory("anno_until")

    site_host_svc: AVAnnotationKey = (
        SiteId(site_id),
        HostName(hostname),
        ServiceName(service) if service else None,
    )

    return site_id, hostname, host_state, service, service_state, fromtime, untiltime, site_host_svc
