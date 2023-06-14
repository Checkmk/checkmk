#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import os
from collections.abc import Collection

from PIL import Image, PngImagePlugin

import cmk.utils.paths
import cmk.utils.store as store

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.plugins.wato.utils import make_confirm_delete_link, mode_registry, redirect, WatoMode
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.theme import theme
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import Dictionary, DropdownChoice, IconSelector, ImageUpload
from cmk.gui.watolib.hosts_and_folders import make_action_link


@mode_registry.register
class ModeIcons(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "icons"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["icons"]

    def title(self) -> str:
        return _("Custom icons")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Icon"),
            breadcrumb,
            form_name="upload_form",
            button_name="_save",
            save_title=_("Upload"),
        )

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
                    "Your icon conflicts with a Checkmk builtin icon. Please "
                    "choose another name for your icon."
                ),
            )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.has_var("_delete"):
            icon_name = request.var("_delete")
            if icon_name in self._load_custom_icons():
                os.remove(
                    "%s/local/share/check_mk/web/htdocs/images/icons/%s.png"
                    % (cmk.utils.paths.omd_root, icon_name)
                )

        elif request.has_var("_save"):
            vs_upload = self._vs_upload()
            icon_info = vs_upload.from_html_vars("_upload_icon")
            vs_upload.validate_value(icon_info, "_upload_icon")
            self._upload_icon(icon_info)

        return redirect(self.mode_url())

    def _upload_icon(self, icon_info):
        # Add the icon category to the PNG comment
        im = Image.open(io.BytesIO(icon_info["icon"][2]))
        im.info["Comment"] = icon_info["category"]
        meta = PngImagePlugin.PngInfo()
        for k, v in im.info.items():
            if isinstance(v, (bytes, str)):
                meta.add_text(k, v, False)

        # and finally save the image
        dest_dir = "%s/local/share/check_mk/web/htdocs/images/icons" % cmk.utils.paths.omd_root
        store.makedirs(dest_dir)
        try:
            file_name = os.path.basename(icon_info["icon"][0])
            im.save(dest_dir + "/" + file_name, "PNG", pnginfo=meta)
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

        html.begin_form("upload_form", method="POST")
        self._vs_upload().render_input("_upload_icon", None)
        html.hidden_fields()
        html.end_form()

        icons = sorted(self._load_custom_icons().items())
        with table_element("icons", _("Custom Icons")) as table:
            for nr, (icon_name, category_name) in enumerate(icons):
                table.row()

                table.cell("#", css=["narrow nowrap"])
                html.write_text(nr)

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
