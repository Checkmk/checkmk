#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Edit global settings of the visual"""

import copy
from collections.abc import Sequence
from typing import Any, cast
from urllib.parse import unquote

from cmk.ccc.user import UserId

from cmk.gui import forms
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pagetypes import (
    make_edit_form_page_menu,
    PagetypeTopics,
    PublishTo,
    SubPagesSpec,
    vs_no_permission_to_publish,
)
from cmk.gui.type_defs import (
    FilterName,
    HTTPVariables,
    InfoName,
    SingleInfos,
    VisualContext,
    VisualName,
    VisualTypeName,
)
from cmk.gui.user_async_replication import user_profile_async_replication_page
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import is_user_with_publish_permissions
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import file_name_and_query_vars_from_url, makeuri_contextless
from cmk.gui.validate import validate_id
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    IconSelector,
    Integer,
    TextAreaUnicode,
    TextInput,
    Transform,
    ValueSpec,
)
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry, VisualType

from ._breadcrumb import visual_page_breadcrumb
from ._filter_valuespecs import VisualFilterList
from ._store import available, delete_local_file, move_visual_to_local, save, TVisual


def page_edit_visual(  # type: ignore[no-untyped-def]
    what: VisualTypeName,
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
    custom_field_handler=None,
    create_handler=None,
    info_handler=None,
    sub_pages: SubPagesSpec | None = None,
    help_text_context: str | HTML | None = None,
) -> None:
    if sub_pages is None:
        sub_pages = []

    visual_type = visual_type_registry[what]()
    if not user.may("general.edit_" + what):
        raise MKAuthException(_("You are not allowed to edit %s.") % visual_type.plural_title)
    visual: dict[str, Any] = {
        "link_from": {},
        "context": {},
        "main_menu_search_terms": [],
    }

    mode = request.get_str_input_mandatory("mode", "edit")
    visualname = request.get_str_input_mandatory("load_name", "")
    oldname = visualname
    owner_user_id = user.id

    def _get_visual(owner_id, mode):
        if visual := all_visuals.get((owner_id, visualname)):
            return visual
        if mode == "clone":
            return _get_visual("", "builtins")
        raise MKUserError(mode, _("The %s does not exist.") % visual_type.title)

    back_url = unquote(request.get_url_input("back", "edit_%s.py" % what))

    if visualname:
        owner_id = request.get_validated_type_input_mandatory(UserId, "owner", user.id)
        visual = _get_visual(owner_id, mode)

        if mode == "edit" and owner_id != "":  # editing built-ins requires copy
            if owner_id != user.id:
                if not user.may("general.edit_foreign_%s" % what):
                    raise MKAuthException(
                        _("You are not allowed to edit foreign %s.") % visual_type.plural_title
                    )
            owner_user_id = owner_id
            title = _("Edit %s") % visual_type.title
        elif mode == "export":
            move_visual_to_local(
                request.get_str_input_mandatory("load_name"),
                request.get_validated_type_input_mandatory(UserId, "owner", user.id),
                all_visuals,
                what,
            )
            raise HTTPRedirect(back_url)
        elif mode == "delete":
            delete_local_file(what, visualname)
            raise HTTPRedirect(back_url)
        else:  # clone explicit or edit from built-in that needs copy
            title = _("Clone %s") % visual_type.title
            visual = copy.deepcopy(visual)
            visual["public"] = False

            # Name conflict -> try new names
            newname, n = visualname, 0
            while (owner_user_id, newname) in all_visuals:
                n += 1
                newname = visualname + "_clone%d" % n
            visual["name"] = newname
            visualname = newname
            oldname = ""  # Prevent renaming
            if owner_id == owner_user_id:
                visual["title"] += _(" (copy)")

        single_infos = visual["single_infos"]

    else:
        title = _("Create %s") % visual_type.title
        mode = "create"
        single_infos = []
        single_infos_raw = request.var("single_infos")
        if single_infos_raw:
            single_infos = single_infos_raw.split(",")
            for key in single_infos:
                if key not in visual_info_registry:
                    raise MKUserError("single_infos", _("The info %s does not exist.") % key)
        visual["single_infos"] = single_infos

    breadcrumb = visual_page_breadcrumb(what, title, mode)
    page_menu = make_edit_form_page_menu(
        breadcrumb,
        dropdown_name=what[:-1],
        mode=mode,
        type_title=visual_type.title,
        type_title_plural=visual_type.plural_title,
        ident_attr_name=visual_type.ident_attr,
        sub_pages=sub_pages,
        form_name="visual",
        visualname=visualname,
    )
    make_header(html, title, breadcrumb, page_menu)

    # A few checkboxes concerning the visibility of the visual. These will
    # appear as boolean-keys directly in the visual dict, but encapsulated
    # in a list choice in the value spec.
    visibility_elements: list[tuple[str, ValueSpec]] = [
        (
            "hidden",
            FixedValue(
                value=True,
                title=_("Hide this %s in the monitor menu") % visual_type.title,
                totext="",
            ),
        ),
        (
            "hidebutton",
            FixedValue(
                value=True,
                title=_("Hide this %s in drop-down menus") % visual_type.title,
                totext="",
            ),
        ),
    ]

    if is_user_with_publish_permissions("visual", user.id, what):
        visibility_elements.append(
            (
                "public",
                PublishTo(
                    publish_all=user.may("general.publish_" + what),
                    publish_groups=user.may("general.publish_" + what + "_to_groups"),
                    publish_sites=user.may("general.publish_" + what + "_to_sites"),
                    type_title=visual_type.title,
                    with_foreign_groups=user.may("general.publish_" + what + "_to_foreign_groups"),
                ),
            )
        )
    else:
        visibility_elements.append(
            (
                "public",
                vs_no_permission_to_publish(
                    type_title=what[:-1],
                    title=_("Make this %s available for other users") % what[:-1].lower(),
                ),
            )
        )

    vs_general = _vs_general(
        single_infos,
        unique_default_name_suggestion(
            what[:-1],
            (visual["name"] for visual in all_visuals.values()),
        ),
        visual_type,
        visibility_elements,
        all_visuals,
        mode,
        what,
    )
    if mode == "clone":
        context_specs = get_context_specs(
            [],
            info_handler(visual) if info_handler else list(visual_info_registry.keys()),
        )
    else:
        context_specs = get_context_specs(
            visual["single_infos"],
            info_handler(visual) if info_handler else list(visual_info_registry.keys()),
        )

    # handle case of save or try or press on search button
    save_and_go = None
    for nr, (title, pagename, _icon) in enumerate(sub_pages):
        if request.var("save%d" % nr):
            save_and_go = pagename

    if save_and_go or request.var("_save") or request.var("save_and_view") or request.var("search"):
        try:
            general_properties = vs_general.from_html_vars("general")

            vs_general.validate_value(general_properties, "general")

            if not general_properties["topic"]:
                general_properties["topic"] = "other"

            old_visual = visual
            # TODO: Currently not editable, but keep settings
            visual = {
                "link_from": old_visual["link_from"],
                "main_menu_search_terms": old_visual["main_menu_search_terms"],
            }

            # Important for saving
            visual["packaged"] = False

            # The dict of the value spec does not match exactly the dict
            # of the visual. We take over some keys...
            for key in [
                "single_infos",
                "name",
                "title",
                "topic",
                "sort_index",
                "is_show_more",
                "description",
                "icon",
                "add_context_to_title",
            ]:
                visual[key] = general_properties[key]

            # ...and import the visibility flags directly into the visual
            for key, _value in visibility_elements:
                visual[key] = general_properties["visibility"].get(key, False)

            if not is_user_with_publish_permissions("visual", user.id, what):
                visual["public"] = False

            if create_handler:
                visual = create_handler(old_visual, visual)

            visual["context"] = process_context_specs(context_specs)

            if request.var("_save") or request.var("save_and_view") or save_and_go:
                if save_and_go:
                    back_url = makeuri_contextless(
                        request,
                        [(visual_type.ident_attr, visual["name"])],
                        filename=save_and_go + ".py",
                    )

                if request.var("save_and_view"):
                    back_vars: HTTPVariables = []
                    back_url_from_vars = request.var("back")
                    if back_url_from_vars:
                        _file_name, query_vars = file_name_and_query_vars_from_url(
                            back_url_from_vars
                        )
                        back_vars = [(varname, value[0]) for varname, value in query_vars.items()]
                    visual_name_var: tuple[str, str] = (visual_type.ident_attr, visual["name"])
                    if visual_name_var not in back_vars:
                        back_vars.append(visual_name_var)

                    back_url = makeuri_contextless(
                        request,
                        back_vars,
                        filename=visual_type.show_url,
                    )

                if transactions.check_transaction():
                    assert owner_user_id is not None
                    # Since we have no way to parse the raw dictionary and Dictionary is also not
                    # typable, we need to hope here that page_dict fits with TVisual. On the mission to at
                    # least add some typing here, we take this shortcut for now. There are way
                    # bigger problems in this class hierarchy than the edit dialog we should solve
                    # first.
                    all_visuals[(owner_user_id, visual["name"])] = cast(TVisual, visual)
                    # Handle renaming of visuals
                    if oldname and oldname != visual["name"]:
                        # -> delete old entry
                        if (owner_user_id, oldname) in all_visuals:
                            del all_visuals[(owner_user_id, oldname)]
                        # -> change visual_name in back parameter
                        if back_url:
                            varstring = visual_type.ident_attr + "="
                            back_url = back_url.replace(
                                varstring + oldname, varstring + visual["name"]
                            )
                    save(what, all_visuals, owner_user_id)
                    user_profile_async_replication_page(
                        back_url=request.get_url_input("back", visual_type.show_url)
                    )

                if not request.var("save_and_view"):
                    flash(_("Your %s has been saved.") % visual_type.title)
                html.reload_whole_page(back_url)
                html.footer()
                return

        except MKUserError as e:
            html.user_error(e)

    with html.form_context("visual", method="POST"):
        html.hidden_field("back", back_url)
        html.hidden_field("mode", mode)
        if request.has_var("owner"):
            html.hidden_field("owner", request.var("owner"))
        html.hidden_field("load_name", oldname)  # safe old name in case user changes it

        # FIXME: Hier werden die Flags aus visibility nicht korrekt geladen. Wäre es nicht besser,
        # diese in einem Unter-Dict zu lassen, anstatt diese extra umzukopieren?
        visib = {}
        for key, _vs in visibility_elements:
            if visual.get(key):
                visib[key] = visual[key]
        visual["visibility"] = visib

        visual["topic"] = (
            visual.get("topic") or "other"
        )  # default to "other" (in case of empty string)
        vs_general.render_input("general", visual)

        if custom_field_handler and custom_field_handler.__name__ != "dashboard_fields_handler":
            custom_field_handler(visual)

        render_context_specs(
            # During view configuration: if a MKUserError is raised BEFORE the visual context is set
            # via 'visual["context"] = process_context_specs(context_specs)' from above then we get a
            # KeyError here and the whole configuration is lost and has to be started from scratch.
            # Example: If no column is choosen.
            visual.get("context", {}),
            context_specs,
            isopen=what != "dashboards",
            help_text=help_text_context,
        )

        if custom_field_handler and custom_field_handler.__name__ == "dashboard_fields_handler":
            custom_field_handler(visual)

        forms.end()
        html.show_localization_hint()

        html.hidden_fields()
    html.footer()


def get_context_specs(
    single_infos: Sequence[InfoName],
    info_keys: Sequence[InfoName],
    ignored_context_choices: Sequence[str] = (),
) -> list[tuple[InfoName, Transform[dict] | VisualFilterList]]:
    single_info_keys = [key for key in info_keys if key in single_infos]
    multi_info_keys = [key for key in info_keys if key not in single_info_keys]

    def host_service_lead(val: tuple[InfoName, Transform[dict] | VisualFilterList]) -> int:
        # Sort is stable in python, thus only prioritize host>service>rest
        if val[0] == "host":
            return 0
        if val[0] == "service":
            return 1
        return 2

    # single infos first, the rest afterwards
    context_specs: list[tuple[InfoName, Transform[dict] | VisualFilterList]] = [
        (info_key, _visual_spec_single(info_key)) for info_key in single_info_keys
    ] + [
        (info_key, spec)
        for info_key in multi_info_keys
        for spec in [_visual_spec_multi(info_key, ignored_context_choices)]
        if spec is not None
    ]

    return sorted(context_specs, key=host_service_lead)


def _visual_spec_single(info_key: InfoName) -> Transform[dict]:
    # VisualInfos have a single_spec, which might declare multiple filters.
    # In this case each spec is as filter value and it is typed(at the moment only Integer & TextInput).
    # Filters at the moment, due to use of url_vars, are string only.
    # At the moment single_info_spec relation to filters is:
    #     for all (i): info.single_spec[i][0]==filter.ident==filter.htmlvars[0]

    # This _visual_spec_single stores direct into the VisualContext, thus it needs to dissosiate
    # the single_spec into separate filters. This transformations are the equivalent of flattening
    # the values into the url, but now they preserve the VisualContext type.

    # In both cases unused keys need to be removed otherwise empty values proliferate
    # either they are saved or they corrupt the VisualContext during merges.

    def from_valuespec(
        values: dict[str, str | int], single_spec: list[tuple[FilterName, ValueSpec]]
    ) -> VisualContext:
        return {
            ident: {ident: str(value)}
            for ident, _vs in single_spec
            for value in [values.get(ident)]
            if value
        }

    def to_valuespec(
        context: VisualContext, single_spec: list[tuple[FilterName, ValueSpec]]
    ) -> dict[str, str | int]:
        return {
            ident: value
            for ident, vs in single_spec
            for value in [context.get(ident, {}).get(ident)]
            if value
        }

    info = visual_info_registry[info_key]()

    return Transform(
        valuespec=Dictionary(
            title=info.title,
            form_isopen=True,
            optional_keys=True,
            elements=info.single_spec,
        ),
        from_valuespec=lambda values: from_valuespec(values, info.single_spec),
        to_valuespec=lambda context: to_valuespec(context, info.single_spec),
    )


def _visual_spec_multi(
    info_key: InfoName, ignored_context_choices: Sequence[str] = ()
) -> VisualFilterList | None:
    info = visual_info_registry[info_key]()
    filter_list = VisualFilterList(
        [info_key], title=info.title, ignored_context_choices=ignored_context_choices
    )
    filter_names = filter_list.filter_names()
    # Skip infos which have no filters available
    return filter_list if filter_names else None


def process_context_specs(
    context_specs: list[tuple[InfoName, Transform[dict] | VisualFilterList]],
) -> VisualContext:
    context: dict[str, Any] = {}
    for info_key, spec in context_specs:
        ident = "context_" + info_key

        attrs = spec.from_html_vars(ident)
        spec.validate_value(dict(attrs), ident)
        context.update(attrs)
    return context


def render_context_specs(
    context: VisualContext,
    context_specs: list[tuple[InfoName, Transform[dict] | VisualFilterList]],
    isopen: bool = True,
    help_text: str | HTML | None = None,
) -> None:
    if not context_specs:
        return

    forms.header(
        _("Context / Search Filters"),
        isopen=isopen,
        show_more_toggle=any(vs.has_show_more() for _title, vs in context_specs if vs is not None),
        help_text=help_text,
    )
    # Trick: the field "context" contains a dictionary with
    # all filter settings, from which the value spec will automatically
    # extract those that it needs.
    for info_key, spec in context_specs:
        forms.section(
            spec.title(),
            is_show_more=(
                spec.has_show_more()
                if isinstance(spec, Transform)
                else all(flt.is_show_more for _title, flt in spec.filter_items() if flt is not None)
            ),
        )
        ident = "context_" + info_key
        spec.render_input(ident, context)


def _vs_general(
    single_infos: SingleInfos,
    default_id: str,
    visual_type: VisualType,
    visibility_elements: list[tuple[str, ValueSpec]],
    all_visuals: dict[tuple[UserId, VisualName], TVisual],
    mode: str,
    what: VisualTypeName,
) -> Dictionary:
    return Dictionary(
        title=_("General properties"),
        render="form",
        optional_keys=False,
        show_more_keys=["description", "add_context_to_title", "sort_index", "is_show_more"],
        elements=[
            single_infos_spec(single_infos),
            (
                "name",
                TextInput(
                    title=_("Unique ID"),
                    help=_(
                        "The ID will be used in URLs that point to a view, e.g. "
                        "<tt>view.py?view_name=<b>myview</b></tt>. It will also be used "
                        "internally for identifying a view. You can create several views "
                        "with the same title but only one per view name. If you create a "
                        "view that has the same view name as a built-in view, then your "
                        "view will override that (shadowing it)."
                    ),
                    regex="^[a-zA-Z0-9_]+$",
                    regex_error=_(
                        "The name of the view may only contain letters, digits and underscores."
                    ),
                    size=50,
                    allow_empty=False,
                    default_value=default_id,
                ),
            ),
            ("title", TextInput(title=_("Title") + "<sup>*</sup>", size=50, allow_empty=False)),
            (
                "description",
                TextAreaUnicode(
                    title=_("Description") + "<sup>*</sup>",
                    rows=4,
                    cols=50,
                ),
            ),
            (
                "add_context_to_title",
                Checkbox(
                    title=_("Context information"),
                    label=_("Add context information to title"),
                    help=_(
                        "Whether or not additional information from the page context "
                        "(filters) should be added to the title given above."
                    ),
                ),
            ),
            (
                "topic",
                DropdownChoice(
                    title=_("Topic in ’Monitor' menu"),
                    default_value="my_workplace",
                    help=_(
                        "Dashboards will be visible in the ‘Monitor’ main menu. "
                        "With this option, you can select in which section of the menu this "
                        "dashboard should be accessible. If you want to define a new "
                        "topic name you can do this <a href='%s'>here</a>."
                    )
                    % "pagetype_topics.py",
                    choices=PagetypeTopics.choices(),
                ),
            ),
            (
                "sort_index",
                Integer(
                    title=_("Sort index"),
                    default_value=99,
                    help=_(
                        "You can customize the order of the %s by changing "
                        "this number. Lower numbers will be sorted first. "
                        "Topics with the same number will be sorted alphabetically."
                    )
                    % visual_type.title,
                ),
            ),
            (
                "is_show_more",
                Checkbox(
                    title=_("Show more"),
                    label=_("Only show the %s if show more is active") % visual_type.title,
                    help=_(
                        "The navigation allows to hide items based on a show "
                        "less / show more toggle. You can specify here whether or "
                        "not this %s should only be shown with show more %s."
                    )
                    % (visual_type.title, visual_type.title),
                ),
            ),
            (
                "icon",
                IconSelector(
                    title=_("Icon"),
                    help=_(
                        "This selection is only relevant if under 'User' "
                        "-> 'Edit Profile' -> 'Mega menue icons' you have selected "
                        "the options 'Per Entry'. If this is the case, you "
                        "select here the icon that will be placed next to your "
                        "Dashboard’s name in the Monitoring menu. You can only "
                        "select one icon (the colored icon) or one icon that is "
                        "complemented with an additional symbol."
                    ),
                ),
            ),
            (
                "visibility",
                Dictionary(
                    title=_("Visibility"),
                    elements=visibility_elements,
                ),
            ),
        ],
        validate=validate_id(
            mode,
            {k: v for k, v in available(what, all_visuals).items() if v["owner"] == user.id},
        ),
    )


def single_infos_spec(single_infos: SingleInfos) -> tuple[str, FixedValue]:
    return (
        "single_infos",
        FixedValue(
            value=single_infos,
            title=_("Show information of single"),
            totext=(
                ", ".join(single_infos)
                if single_infos
                else _("Not restricted to showing a specific object.")
            ),
        ),
    )
