#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Collection

import cmk.utils.paths
from cmk.utils.images import CMKImage, ImageType

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import Permission, PermissionRegistry
from cmk.gui.table import table_element
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link
from cmk.gui.valuespec import Dictionary, DropdownChoice, IconSelector, ImageUpload
from cmk.gui.wato import PERMISSION_SECTION_WATO
from cmk.gui.watolib.hosts_and_folders import make_action_link
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode


class ModeIcons(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "icons"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["icons"]

    def title(self) -> str:
        return _("Custom icons")

    def _load_custom_icons(self):
        s = IconSelector(show_builtin_icons=False, with_emblem=False)
        return s.available_icons(only_local=True)

    def _vs_upload(self):
        return Dictionary(
            title=_("Upload icon"),
            optional_keys=False,
            render="form",
            elements=[
                (
                    "icon",
                    ImageUpload(
                        title=_("Icon"),
                        allowed_extensions=[".png"],
                        mime_types=["image/png"],
                        max_size=(80, 80),
                        validate=self._validate_icon,
                    ),
                ),
                (
                    "category",
                    DropdownChoice(
                        title=_("Category"),
                        choices=active_config.wato_icon_categories,
                        no_preselect_title="",
                    ),
                ),
            ],
        )

    def _validate_icon(self, value, varprefix):
        file_name = value[0]
        browser_url = theme.url("images/icon_%s" % file_name)
        if os.path.exists(
            f"{cmk.utils.paths.omd_root}/share/check_mk/web/htdocs/{browser_url}"
        ) or os.path.exists(
            f"{cmk.utils.paths.omd_root}/share/check_mk/web/htdocs/images/icons/{file_name}"
        ):
            raise MKUserError(
                varprefix,
                _(
                    "Your icon conflicts with a Checkmk built-in icon. Please "
                    "choose another name for your icon."
                ),
            )

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.has_var("_delete"):
            icon_name = request.var("_delete")
            if icon_name in self._load_custom_icons():
                os.remove(
                    f"{cmk.utils.paths.omd_root}/local/share/check_mk/web/htdocs/images/icons/{icon_name}.png"
                )

        elif request.has_var("_save"):
            vs_upload = self._vs_upload()
            icon_info = vs_upload.from_html_vars("_upload_icon")
            vs_upload.validate_value(icon_info, "_upload_icon")
            self._upload_icon(icon_info)

        return redirect(self.mode_url())

    def _upload_icon(self, icon_info):
        dest_dir = cmk.utils.paths.omd_root / "local/share/check_mk/web/htdocs/images/icons"
        dest_dir.mkdir(mode=0o770, exist_ok=True, parents=True)
        try:
            image = CMKImage(icon_info["icon"][2], ImageType.PNG)
            image.add_metadata("Comment", icon_info["category"])
            file_name = os.path.basename(icon_info["icon"][0])
            image.save(dest_dir / file_name, ImageType.PNG)
        except OSError as e:
            # Might happen with interlaced PNG files and PIL version < 1.1.7
            raise MKUserError(None, _("Unable to upload icon: %s") % e)

    def page(self) -> None:
        html.p(
            _(
                "Here you can add icons, for example to use them in bookmarks or "
                "in custom actions of views. Allowed are single PNG image files "
                "with a maximum size of 80x80 px. Custom actions have to be defined "
                "in the global settings and can be used in the custom icons rules "
                "of hosts and services."
            )
        )

        with html.form_context("upload_form", method="POST"):
            self._vs_upload().render_input("_upload_icon", None)
            html.button(varname="_save", title=_("Upload"), cssclass="hot")
            html.hidden_fields()

        icons = sorted(self._load_custom_icons().items())
        with table_element("icons", _("Custom Icons")) as table:
            for nr, (icon_name, category_name) in enumerate(icons):
                table.row()

                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)

                table.cell(_("Actions"), css=["buttons"])
                category = IconSelector.category_alias(category_name)
                delete_url = make_confirm_delete_link(
                    url=make_action_link([("mode", "icons"), ("_delete", icon_name)]),
                    title=_("Delete icon #%d") % nr,
                    suffix=icon_name,
                    message=_("Category: %s") % category,
                )
                html.icon_button(delete_url, _("Delete this Icon"), "delete")

                table.cell(_("Icon"), html.render_icon(icon_name), css=["buttons"])
                table.cell(_("Name"), icon_name)
                table.cell(_("Category"), category)


def register(
    mode_registry: ModeRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    mode_registry.register(ModeIcons)

    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="icons",
            title=_l("Manage custom icons"),
            description=_l("Upload or delete custom icons"),
            defaults=["admin"],
        )
    )
