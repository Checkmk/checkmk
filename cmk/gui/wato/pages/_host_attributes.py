#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from typing import cast, Literal

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostName

from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui import forms
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.html import quick_setup_render_link
from cmk.gui.utils.html import HTML as HTML
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import FixedValue, ValueSpec
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeValueSpec,
    get_sorted_host_attribute_topics,
    get_sorted_host_attributes_by_topic,
)
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    folder_from_request,
    Host,
    SearchFolder,
)

#   "host"        -> normal host edit dialog
#   "cluster"     -> normal host edit dialog
#   "folder"      -> properties of folder or file
#   "host_search" -> host search dialog
#   "bulk"        -> bulk change
DialogIdent = Literal["host", "cluster", "folder", "host_search", "bulk"]


def _get_single_host(hosts: Mapping[str, object]) -> Host | None:
    if len(hosts) == 1 and (host := next(iter(hosts.values()))) and isinstance(host, Host):
        return host
    return None


# TODO: Wow, this function REALLY has to be cleaned up
def configure_attributes(
    new: bool,
    hosts: Mapping[str, Host | Folder | None],
    for_what: DialogIdent,
    parent: Folder | SearchFolder | None,
    myself: Folder | None = None,
    without_attributes: Sequence[str] | None = None,
    varprefix: str = "",
    basic_attributes: Sequence[tuple[str, ValueSpec, object]] | None = None,
) -> None:
    """Show HTML form for editing attributes.

    new: Boolean flag if this is a creation step or editing
    parent: The parent folder of the objects to configure
    myself: For mode "folder" the folder itself or None, if we edit a new folder
            This is needed for handling mandatory attributes.

    This is the counterpart of "collect_attributes". Another place which
    is related to these HTTP variables and so on is SearchFolder.
    """
    if without_attributes is None:
        without_attributes = []
    if basic_attributes is None:
        basic_attributes = []

    # Collect dependency mapping for attributes (attributes that are only
    # visible, if certain host tags are set).
    dependency_mapping_tags = {}
    dependency_mapping_roles = {}
    inherited_tags = {}

    volatile_topics = []
    hide_attributes = []
    show_more_mode: bool = False

    show_more_mode = user.show_mode != "default_show_less"
    is_cse = cmk_version.edition(paths.omd_root) == cmk_version.Edition.CSE

    for topic_id, topic_title in get_sorted_host_attribute_topics(for_what, new):
        topic_is_volatile = True  # assume topic is sometimes hidden due to dependencies
        topic_attributes = get_sorted_host_attributes_by_topic(topic_id)

        single_edit_host = _get_single_host(hosts)

        forms.header(
            topic_title,
            isopen=topic_id in ["basic", "address", "monitoring_agents"],
            table_id=topic_id,
            show_more_toggle=any(attribute.is_show_more() for attribute in topic_attributes),
            show_more_mode=show_more_mode,
        )

        if topic_id == "management_board":
            message = _(
                "<b>This feature will be deprecated in a future version of Checkmk.</b>"
                "<br>Please do not configure management boards in here anymore. "
                "Monitor the management boards via a dedicated host using <a href='%s'>IPMI</a>"
                " or SNMP.<br><a href='%s' target='_blank'>Read more about management boards.</a>"
            ) % (
                makeuri_contextless(
                    request,
                    [
                        ("mode", "edit_ruleset"),
                        ("varname", RuleGroup.SpecialAgents("ipmi_sensors")),
                    ],
                    filename="wato.py",
                ),
                "https://checkmk.com/blog/monitoring-management-boards",
            )
            forms.warning_message(message)

        if topic_id == "basic":
            for attr_varprefix, vs, default_value in basic_attributes:
                forms.section(
                    _u(title) if (title := vs.title()) is not None else None,
                    is_required=not vs.allow_empty(),
                )
                vs.render_input(attr_varprefix, default_value)

        for attr in topic_attributes:
            attrname = attr.name()
            if attrname in without_attributes:
                continue  # e.g. needed to skip ipaddress in CSV-Import

            # Hide snmp tag option in CSE. Registration is still needed because
            # connection test page should still be functional
            if is_cse and attrname == "tag_snmp_ds":
                hide_attributes.append(attr.name())

            # Determine visibility information if this attribute is not always hidden
            if attr.is_visible(for_what, new):
                depends_on_tags = attr.depends_on_tags()
                depends_on_roles = attr.depends_on_roles()
                # Add host tag dependencies, but only in host mode. In other
                # modes we always need to show all attributes.
                if for_what in ["host", "cluster"] and depends_on_tags:
                    dependency_mapping_tags[attrname] = depends_on_tags

                if depends_on_roles:
                    dependency_mapping_roles[attrname] = depends_on_roles

                if for_what not in ["host", "cluster"]:
                    topic_is_volatile = False

                elif not depends_on_tags and not depends_on_roles:
                    # One attribute is always shown -> topic is always visible
                    topic_is_volatile = False
            else:
                hide_attributes.append(attr.name())

            # "bulk": determine, if this attribute has the same setting for all hosts.
            values, num_have_locked_it, num_haveit = _determine_attribute_settings(attrname, hosts)

            # The value of this attribute is unique amongst all hosts if
            # either no host has a value for this attribute, or all have
            # one and have the same value
            unique = num_haveit == 0 or (len(values) == 1 and num_haveit == len(hosts))

            # Collect information about attribute values inherited from folder.
            # This information is just needed for informational display to the user.
            # This does not apply in "host_search" mode.
            inherited_from: HTML | None = None
            inherited_value = None
            has_inherited = False
            container = None

            if attr.show_inherited_value():
                if for_what in ["host", "cluster"]:
                    try:
                        host_name = request.get_ascii_input("host")
                    except MKUserError:
                        host_name = None
                    url = folder_from_request(request.var("folder"), host_name).edit_url()

                container = parent  # container is of type Folder
                while container:
                    if attrname in container.attributes:
                        assert not isinstance(container, SearchFolder)
                        url = container.edit_url()
                        inherited_from = HTML.with_escaping(
                            _("Inherited from ")
                        ) + HTMLWriter.render_a(container.title(), href=url)

                        # Mypy can not help here with the dynamic key
                        inherited_value = container.attributes[attrname]  # type: ignore[literal-required]
                        has_inherited = True
                        if attr.is_tag_attribute:
                            inherited_tags["attr_%s" % attrname] = inherited_value
                        break

                    container = container.parent()

            if not container:  # We are the root folder - we inherit the default values
                inherited_from = HTML.with_escaping(_("Default value"))
                inherited_value = attr.default_value()
                # Also add the default values to the inherited values dict
                if attr.is_tag_attribute:
                    inherited_tags["attr_%s" % attrname] = inherited_value

            # Checkbox for activating this attribute

            # Determine current state of visibility: If the form has already been submitted (i.e. search
            # or input error), then we take the previous state of the box. In search mode we make those
            # boxes active that have an empty string as default value (simple text boxed). In bulk
            # mode we make those attributes active that have an explicitely set value over all hosts.
            # In host and folder mode we make those attributes active that are currently set.

            # Also determine, if the attribute can be switched off at all. Problematic here are
            # mandatory attributes. We must make sure, that at least one folder/file/host in the
            # chain defines an explicit value for that attribute. If we show a host and no folder/file
            # inherits an attribute to that host, the checkbox will be always active and locked.
            # The same is the case if we show a file/folder and at least one host below this
            # has not set that attribute. In case of bulk edit we never lock: During bulk edit no
            # attribute ca be removed anyway.

            checkbox_name = for_what + "_change_%s" % attrname
            cb = html.get_checkbox(checkbox_name)
            force_entry = False
            disabled = False

            # first handle mandatory cases
            if (
                for_what == "folder"
                and attr.is_mandatory()
                and myself
                and _some_host_hasnt_set(myself, attrname)
                and not has_inherited
            ):
                force_entry = True
                active = True
            elif for_what in ["host", "cluster"] and attr.is_mandatory() and not has_inherited:
                force_entry = True
                active = True
            elif cb is not None:
                active = cb  # get previous state of checkbox
            elif for_what == "bulk":
                active = unique and len(values) > 0
            elif for_what == "folder" and myself:
                active = attrname in myself.attributes
            elif for_what in ["host", "cluster"] and single_edit_host:
                active = attrname in single_edit_host.attributes
            else:
                active = False

            is_editable = attr.editable() and attr.may_edit() and num_have_locked_it == 0
            if for_what == "host_search":
                is_editable = True

            if not is_editable:
                if active:
                    force_entry = True
                else:
                    disabled = True

            if (for_what in ["host", "cluster"] and parent and parent.locked_hosts()) or (
                for_what == "folder" and myself and myself.locked()
            ):
                checkbox_code = None
            elif force_entry:
                checkbox_code = html.render_checkbox(
                    "ignored_" + checkbox_name, disabled="disabled"
                )
                checkbox_code += html.render_hidden_field(checkbox_name, "on")
            else:
                onclick = (
                    "cmk.wato.fix_visibility(); cmk.wato.toggle_attribute(this, '%s');" % attrname
                )
                checkbox_kwargs = {"disabled": "disabled"} if disabled else {}
                checkbox_code = html.render_checkbox(
                    checkbox_name, active, onclick=onclick, **checkbox_kwargs
                )

            forms.section(
                _u(attr.title()),
                checkbox=checkbox_code,
                section_id="attr_" + attrname,
                is_show_more=attr.is_show_more(),
                is_changed=active,
            )
            html.help(attr.help())

            if len(values) == 1:
                defvalue = values[0]
            elif attr.is_checkbox_tag:
                defvalue = True
            else:
                defvalue = attr.default_value()

            if not new and not is_editable:
                # In edit mode only display non editable values, don't show the
                # input fields
                html.open_div(id_="attr_hidden_%s" % attrname, style="display:none;")
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(id_="attr_visible_%s" % attrname, class_=["inherited"])

            else:
                # Now comes the input fields and the inherited / default values
                # as two DIV elements, one of which is visible at one time.

                # DIV with the input elements
                html.open_div(
                    id_="attr_entry_%s" % attrname, style="display: none;" if not active else None
                )
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(
                    class_="inherited",
                    id_="attr_default_%s" % attrname,
                    style="display: none;" if active else None,
                )

            #
            # DIV with actual / inherited / default value
            #

            # in bulk mode we show inheritance only if *all* hosts inherit
            explanation: HTML = HTML.empty()
            value: object = None
            if for_what == "bulk":
                if num_haveit == 0:
                    assert inherited_from is not None
                    explanation = " (" + inherited_from + ")"
                    value = inherited_value
                elif not unique:
                    explanation = HTML.with_escaping(
                        _("This value differs between the selected hosts.")
                    )
                else:
                    value = values[0]

            elif for_what in ["host", "cluster", "folder"]:
                if not new and not is_editable and active:
                    value = values[0]
                else:
                    if inherited_from is not None:
                        explanation = " (" + inherited_from + ")"
                    value = inherited_value

            if for_what != "host_search" and not (for_what == "bulk" and not unique):
                _tdclass, content = attr.paint(value, HostName(""))
                if not content:
                    content = _("empty")

                if isinstance(attr, ABCHostAttributeValueSpec):
                    html.open_b()
                    html.write_text_permissive(content)
                    html.close_b()
                elif isinstance(attr, str):
                    html.b(_u(cast(str, content)))
                else:
                    html.b(content)

            html.write_text_permissive(explanation)
            html.close_div()

        # if host is managed by a config bundle, show the source (which is not a real attribute)
        if (
            topic_id == "basic"
            and single_edit_host
            and (locked_by := single_edit_host.locked_by())
            and is_locked_by_quick_setup(locked_by, check_reference_exists=False)
        ):
            vs = FixedValue(
                value=locked_by["instance_id"],
                title=_u("Source"),
                totext=quick_setup_render_link(locked_by),
            )
            forms.section(vs.title())
            vs.render_input("_internal_source", locked_by["instance_id"])

        if topic_is_volatile:
            volatile_topics.append(topic_id)

    forms.end()

    dialog_properties = {
        "inherited_tags": inherited_tags,
        "check_attributes": list(
            set(dependency_mapping_tags.keys())
            | set(dependency_mapping_roles.keys())
            | set(hide_attributes)
        ),
        "aux_tags_by_tag": active_config.tags.get_aux_tags_by_tag(),
        "depends_on_tags": dependency_mapping_tags,
        "depends_on_roles": dependency_mapping_roles,
        "volatile_topics": volatile_topics,
        "user_roles": user.role_ids,
        "hide_attributes": hide_attributes,
    }
    html.javascript(
        "cmk.wato.prepare_edit_dialog(%s);"
        "cmk.wato.fix_visibility();" % json.dumps(dialog_properties)
    )


def _determine_attribute_settings(
    attrname: str, hosts: Mapping[str, Host | Folder | None]
) -> tuple[list[object], int, int]:
    values = []
    num_have_locked_it = 0
    num_haveit = 0
    for host in hosts.values():
        if not host:
            continue

        locked_by = host.attributes.get("locked_by")
        locked_attributes = host.attributes.get("locked_attributes")
        if locked_by and locked_attributes and attrname in locked_attributes:
            num_have_locked_it += 1

        if attrname in host.attributes:
            num_haveit += 1
            if host.attributes.get(attrname) not in values:
                values.append(host.attributes.get(attrname))
    return values, num_have_locked_it, num_haveit


def _some_host_hasnt_set(folder: Folder, attrname: str) -> bool:
    """Check if at least one host in a folder (or its subfolders)
    has not set a certain attribute. This is needed for the validation
    of mandatory attributes."""
    # Check subfolders
    for subfolder in folder.subfolders():
        # If the attribute is not set in the subfolder, we need
        # to check all hosts and that folder.
        if attrname not in subfolder.attributes and _some_host_hasnt_set(subfolder, attrname):
            return True

    # Check hosts in this folder
    for host in folder.hosts().values():
        if attrname not in host.attributes:
            return True

    return False
