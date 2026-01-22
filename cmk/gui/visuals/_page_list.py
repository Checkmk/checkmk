#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Show a list of all visuals of a given type with actions to delete/clone/edit"""

from collections.abc import Callable, Iterable

from cmk.ccc.user import UserId
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    doc_reference_to_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pagetypes import customize_page_menu
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import (
    HTTPVariables,
    IconNames,
    StaticIcon,
    VisualName,
    VisualPublic,
    VisualTypeName,
)
from cmk.gui.user_async_replication import user_profile_async_replication_page
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    make_confirm_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
    urlencode,
)
from cmk.gui.visuals.type import visual_type_registry
from cmk.mkp_tool import PackageName

from ._breadcrumb import visual_page_breadcrumb
from ._store import (
    available,
    get_installed_packages,
    local_file_exists,
    published_to_user,
    save,
    TVisual,
)


# TODO: This code has been copied to a new live into htdocs/pagetypes.py
# We need to convert all existing page types (views, dashboards, reports)
# to pagetypes.py and then remove this function!
def page_list(
    what: VisualTypeName,
    title: str,
    visuals: dict[tuple[UserId, VisualName], TVisual],
    user_permissions: UserPermissions,
    custom_columns: Iterable[tuple[HTMLContent, Callable[[TVisual], HTMLContent]]] | None = None,
    render_custom_buttons: Callable[[VisualName, TVisual], None] | None = None,
    render_custom_columns: Callable[[Table, VisualName, TVisual], None] | None = None,
    custom_page_menu_entries: Callable[[], Iterable[PageMenuEntry]] | None = None,
    check_deletable_handler: (
        Callable[[dict[tuple[UserId, VisualName], TVisual], UserId, str], bool] | None
    ) = None,
) -> None:
    if custom_columns is None:
        custom_columns = []

    what_s = what[:-1]
    if not user.may("general.edit_" + what):
        raise MKAuthException(_("Sorry, you lack the permission for editing this type of visuals."))

    breadcrumb = visual_page_breadcrumb(what, title, "list")

    visual_type = visual_type_registry[what]()
    visual_plural_title = visual_type.plural_title.title()
    topic_entries = []

    if what == "dashboards":
        topic_entries.append(
            PageMenuEntry(
                title=_("Add dashboard"),
                icon_name=StaticIcon(IconNames.new),
                item=make_simple_link("dashboard.py?mode=create"),
                is_shortcut=True,
                is_suggested=True,
            )
        )
    else:
        topic_entries.append(
            PageMenuEntry(
                title=_("Add %s") % visual_type.title,
                icon_name=StaticIcon(IconNames.new),
                item=make_simple_link("create_%s.py" % what_s),
                is_shortcut=True,
                is_suggested=True,
            )
        )

    current_type_dropdown = PageMenuDropdown(
        name=what,
        title=visual_plural_title,
        topics=[
            PageMenuTopic(
                title=visual_plural_title,
                entries=topic_entries
                + (list(custom_page_menu_entries()) if custom_page_menu_entries else []),
            ),
        ],
    )

    page_menu = customize_page_menu(
        breadcrumb,
        current_type_dropdown,
        what,
    )

    _add_doc_references(page_menu, what, visual_plural_title)

    make_header(html, title, breadcrumb, page_menu)

    for message in get_flashed_messages():
        html.show_message(message.msg)

    # Deletion of visuals
    delname = request.var("_delete")
    if delname and transactions.check_transaction():
        if user.may("general.delete_foreign_%s" % what):
            user_id: UserId | None = request.get_validated_type_input_mandatory(
                UserId, "_user_id", user.id
            )
        else:
            user_id = user.id
        assert user_id is not None
        try:
            if check_deletable_handler:
                check_deletable_handler(visuals, user_id, delname)

            del visuals[(user_id, delname)]
            save(what, visuals, user_id)
            user_profile_async_replication_page(
                back_url=request.get_url_input("back", visual_type.show_url)
            )
            flash(_("Your %s has been deleted.") % visual_type.title)
            raise HTTPRedirect(url=html.request.path, code=303)
        except MKUserError as e:
            html.user_error(e)

    available_visuals = available(what, visuals, user_permissions)
    installed_packages: dict[str, PackageName | None] = get_installed_packages(what)
    for source, title1, visual_group in _partition_visuals(visuals, what):
        if not visual_group:
            continue

        html.h3(title1, class_="table")
        with table_element(css="data", limit=False) as table:
            for owner, visual_name, visual in visual_group:
                table.row(css=["data"])

                # Actions
                table.cell(_("Actions"), css=["buttons visuals"])

                is_packaged = visual["packaged"]
                backurl = urlencode(makeuri(request, []))

                # Edit
                if (
                    owner == user.id
                    or (owner != UserId.builtin() and user.may("general.edit_foreign_%s" % what))
                ) and not is_packaged:
                    edit_vars: HTTPVariables
                    if what == "dashboards":
                        edit_vars = [
                            ("mode", "edit_settings"),
                            ("name", visual_name),
                            ("back", backurl),
                        ]
                        filename = "dashboard.py"

                    else:
                        edit_vars = [
                            ("mode", "edit"),
                            ("load_name", visual_name),
                            ("back", backurl),
                        ]
                        filename = "edit_%s.py" % what_s

                    if owner != user.id:
                        edit_vars.append(("owner", owner))

                    edit_url = makeuri_contextless(
                        request,
                        edit_vars,
                        filename=filename,
                    )
                    html.icon_button(edit_url, _("Edit"), StaticIcon(IconNames.edit))

                # Custom buttons - visual specific
                if not is_packaged and render_custom_buttons:
                    render_custom_buttons(visual_name, visual)

                # Clone / Customize
                buttontext = _("Create a private copy of this")

                if what == "dashboards":
                    clone_url = makeuri_contextless(
                        request,
                        [
                            ("mode", "clone"),
                            ("owner", owner),
                            ("name", visual_name),
                            ("back", backurl),
                        ],
                        filename="dashboard.py",
                    )
                else:
                    clone_url = makeuri_contextless(
                        request,
                        [
                            ("mode", "clone"),
                            ("owner", owner),
                            ("load_name", visual_name),
                            ("back", backurl),
                        ],
                        filename="edit_%s.py" % what_s,
                    )
                html.icon_button(clone_url, buttontext, StaticIcon(IconNames.clone))

                # Packaged visuals have built-in user as owner, so we have to
                # make sure to not show packaged related icons for built-in
                # visuals
                if user.may("wato.manage_mkps") and source != "builtin":
                    _render_extension_package_icons(
                        table,
                        visual_name,
                        what,
                        owner,
                        what_s,
                        installed_packages,
                        is_packaged,
                        backurl,
                    )

                # Delete
                if (
                    owner
                    and (owner == user.id or user.may("general.delete_foreign_%s" % what))
                    and not is_packaged
                ):
                    add_vars: HTTPVariables = [("_delete", visual_name)]
                    confirm_message = _("ID: %s") % visual_name
                    if owner != user.id:
                        add_vars.append(("_user_id", owner))
                        confirm_message += "<br>" + _("Owner: %s") % owner
                    html.icon_button(
                        make_confirm_delete_link(
                            url=makeactionuri(request, transactions, add_vars),
                            title=_("Delete %s") % visual_type.title,
                            suffix=str(visual["title"]),
                            message=confirm_message,
                        ),
                        _("Delete"),
                        StaticIcon(IconNames.delete),
                    )

                # visual Name
                table.cell(_("ID"), visual_name)

                # Title
                table.cell(_("Title"))
                title2 = _u(str(visual["title"]))
                if _visual_can_be_linked(what, visual_name, available_visuals, visual, owner):
                    show_url = makeuri_contextless(
                        request,
                        [(visual_type_registry[what]().ident_attr, visual_name), ("owner", owner)],
                        filename="%s.py" % what_s,
                    )
                    html.a(
                        title2,
                        href=show_url,
                        target="_blank" if what_s == "report" else None,
                    )
                else:
                    html.write_text_permissive(title2)
                html.help(_u(str(visual["description"])))

                # Custom cols
                for title3, renderer in custom_columns:
                    table.cell(title3, renderer(visual))

                # Owner
                if owner == UserId.builtin():
                    ownertxt = "<i>" + _("built-in") + "</i>"
                else:
                    ownertxt = owner
                table.cell(_("Owner"), ownertxt)

                if what == "dashboards":
                    table.cell(_("Menu placement"), _("Hidden") if visual["hidden"] else _("Shown"))
                    table.cell(_("Internal access"), _internal_access_state_text(visual["public"]))
                else:
                    table.cell(_("Public"), published_to_user(visual) and _("yes") or _("no"))
                    table.cell(_("Hidden"), visual["hidden"] and _("yes") or _("no"))

                if render_custom_columns:
                    render_custom_columns(table, visual_name, visual)

    html.footer()


def _internal_access_state_text(visual_public: VisualPublic) -> str:
    result: str = _("Only me")
    if isinstance(visual_public, tuple):
        if visual_public[0] == "contact_groups":
            result = _("Contact groups")
        elif visual_public[0] == "sites":
            result = _("Site users")
    elif visual_public is True:
        result = _("All users")

    return result


def _render_extension_package_icons(
    table: Table,
    visual_name: VisualName,
    what: VisualTypeName,
    owner: UserId,
    what_s: str,
    installed_packages: dict[str, PackageName | None],
    is_packaged: object,
    backurl: str,
) -> None:
    """Render icons needed for extension package handling of visuals"""
    if not is_packaged:
        export_url = make_confirm_link(
            url=makeuri_contextless(
                request,
                [
                    ("mode", "export"),
                    ("owner", owner),
                    ("load_name", visual_name),
                    ("back", backurl),
                ],
                filename="edit_%s.py" % what_s,
            ),
            title=_("Clone %s for packaging") % what_s,
            message=_("ID: %s") % visual_name,
            confirm_button=_("Clone"),
            cancel_button=_("Cancel"),
        )

        clone_icon: StaticIcon = StaticIcon(
            IconNames.mkps,
            emblem="add",
        )
        if local_file_exists(what, visual_name):
            html.static_icon(
                clone_icon,
                title=_("This %s is already available for packaging as extension package") % what_s,
                css_classes=["service_button", "disabled", "tooltip"],
            )
        else:
            html.icon_button(
                url=export_url,
                title=_("Clone this %s for packaging as extension package") % what_s,
                icon=clone_icon,
            )
        return

    if not (mkp_name := installed_packages.get(visual_name)):
        delete_url = make_confirm_delete_link(
            url=makeuri_contextless(
                request,
                [
                    ("mode", "delete"),
                    ("owner", owner),
                    ("load_name", visual_name),
                    ("back", backurl),
                ],
                filename="edit_%s.py" % what_s,
            ),
            title=_("Remove %s from extensions") % what_s,
            message=_("ID: %s") % visual_name,
            confirm_button=_("Remove"),
            cancel_button=_("Cancel"),
        )
        html.icon_button(
            url=delete_url,
            title=_("Remove this %s from the extension packages module") % what_s,
            icon=StaticIcon(IconNames.delete),
        )

    html.icon_button(
        "wato.py?mode=mkps",
        _("Go to extension packages"),
        StaticIcon(
            IconNames.mkps,
            emblem="more",
        ),
    )

    table.cell(_("State"), css=["buttons"])
    if mkp_name:
        html.static_icon(
            StaticIcon(IconNames.mkps),
            title=_("This %s is provided via the MKP '%s'") % (what_s, mkp_name),
        )
    else:
        html.static_icon(
            StaticIcon(IconNames.mkps),
            title=_("This %s can be packaged with the extension packages module") % what_s,
        )


def _add_doc_references(
    page_menu: PageMenu,
    what: VisualTypeName,
    visual_plural_title: str,
) -> None:
    # general docs for interface related visuals
    if what in ["views", "dashboards"]:
        page_menu.add_doc_reference(_("The user interface"), DocReference.USER_INTERFACE)
    # specific docs for visual types
    doc_reference_to_page_menu(page_menu, what, visual_plural_title)


def _visual_can_be_linked(
    what: VisualTypeName,
    visual_name: VisualName,
    user_visuals: dict[VisualName, TVisual],
    visual: TVisual,
    owner: UserId,
) -> bool:
    if owner == user.id or user.may("general.edit_foreign_%s" % what):
        return True

    # Is this the highest priority visual that the user has available?
    if user_visuals.get(visual_name) != visual:
        return False

    return bool(visual["public"])


def _partition_visuals(
    visuals: dict[tuple[UserId, VisualName], TVisual], what: str
) -> list[tuple[str, str, list[tuple[UserId, VisualName, TVisual]]]]:
    keys_sorted = sorted(visuals.keys(), key=lambda x: (x[1], x[0]))

    my_visuals, foreign_visuals, builtin_visuals, packaged_visuals = [], [], [], []
    for owner, visual_name in keys_sorted:
        visual = visuals[(owner, visual_name)]
        if owner == UserId.builtin() and (
            (not visual["packaged"] and not user.may(f"{what[:-1]}.{visual_name}"))
            or (visual["packaged"] and not user.may(f"{what[:-1]}.{visual_name}_packaged"))
        ):
            continue  # not allowed to see this view

        if visual["packaged"] and user.may("general.see_packaged_%s" % what):
            packaged_visuals.append((owner, visual_name, visual))
            continue

        if visual["public"] and owner == UserId.builtin():
            builtin_visuals.append((owner, visual_name, visual))
        elif owner == user.id:
            my_visuals.append((owner, visual_name, visual))
        elif (published_to_user(visual) and owner != UserId.builtin()) or user.may(
            "general.edit_foreign_%s" % what
        ):
            foreign_visuals.append((owner, visual_name, visual))

    return [
        ("custom", _("Customized"), my_visuals),
        ("foreign", _("Owned by other users"), foreign_visuals),
        ("packaged", _("Extensions"), packaged_visuals),
        ("builtin", _("Built-in"), builtin_visuals),
    ]
