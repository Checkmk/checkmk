#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import six

import cmk.utils.paths
import cmk.utils.store

import cmk.gui.config as config
from cmk.gui.table import table_element
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    IconSelector,
    ImageUpload,
    DropdownChoice,
    Dictionary,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    wato_confirm,
    global_buttons,
    make_action_link,
)


@mode_registry.register
class ModeIcons(WatoMode):
    @classmethod
    def name(cls):
        return "icons"

    @classmethod
    def permissions(cls):
        return ["icons"]

    def title(self):
        return _('Manage Icons')

    def buttons(self):
        back_url = html.get_url_input("back", "")
        if back_url:
            html.context_button(_("Back"), back_url, "back")
        else:
            global_buttons()

    def _load_custom_icons(self):
        s = IconSelector()
        return s.available_icons(only_local=True)

    def _vs_upload(self):
        return Dictionary(title=_('Icon'),
                          optional_keys=False,
                          render="form",
                          elements=[('icon',
                                     ImageUpload(
                                         title=_('Icon'),
                                         allow_empty=False,
                                         max_size=(80, 80),
                                         validate=self._validate_icon,
                                     )),
                                    ('category',
                                     DropdownChoice(
                                         title=_('Category'),
                                         choices=config.wato_icon_categories,
                                         no_preselect=True,
                                     ))])

    def _validate_icon(self, value, varprefix):
        file_name = value[0]
        browser_url = html.theme_url("images/icon_%s" % file_name)
        if os.path.exists("%s/share/check_mk/web/htdocs/%s" % (cmk.utils.paths.omd_root, browser_url)) \
           or os.path.exists("%s/share/check_mk/web/htdocs/images/icons/%s" % (cmk.utils.paths.omd_root, file_name)):
            raise MKUserError(
                varprefix,
                _('Your icon conflicts with a Check_MK builtin icon. Please '
                  'choose another name for your icon.'))

    def action(self):
        if html.request.has_var("_delete"):
            icon_name = html.request.var("_delete")
            if icon_name in self._load_custom_icons():
                c = wato_confirm(_("Confirm Icon deletion"),
                                 _("Do you really want to delete the icon <b>%s</b>?") % icon_name)
                if c:
                    os.remove("%s/local/share/check_mk/web/htdocs/images/icons/%s.png" %
                              (cmk.utils.paths.omd_root, icon_name))
                elif c is False:
                    return ""
                else:
                    return

        elif html.request.has_var("_do_upload"):
            vs_upload = self._vs_upload()
            icon_info = vs_upload.from_html_vars('_upload_icon')
            vs_upload.validate_value(icon_info, '_upload_icon')
            self._upload_icon(icon_info)

    def _upload_icon(self, icon_info):
        # Add the icon category to the PNG comment
        from PIL import Image, PngImagePlugin
        from StringIO import StringIO
        im = Image.open(StringIO(icon_info['icon'][2]))
        im.info['Comment'] = icon_info['category']
        meta = PngImagePlugin.PngInfo()
        for k, v in im.info.iteritems():
            if isinstance(v, (six.binary_type, six.text_type)):
                meta.add_text(k, v, 0)

        # and finally save the image
        dest_dir = "%s/local/share/check_mk/web/htdocs/images/icons" % cmk.utils.paths.omd_root
        cmk.utils.store.makedirs(dest_dir)
        try:
            file_name = os.path.basename(icon_info['icon'][0])
            im.save(dest_dir + '/' + file_name, 'PNG', pnginfo=meta)
        except IOError as e:
            # Might happen with interlaced PNG files and PIL version < 1.1.7
            raise MKUserError(None, _('Unable to upload icon: %s') % e)

    def page(self):
        html.h3(_("Upload Icon"))
        html.p(_("Allowed are single PNG image files with a maximum size of 80x80 px."))

        html.begin_form('upload_form', method='POST')
        self._vs_upload().render_input('_upload_icon', None)
        html.button('_do_upload', _('Upload'), 'submit')

        html.hidden_fields()
        html.end_form()

        icons = sorted(self._load_custom_icons().items())
        with table_element("icons", _("Custom Icons")) as table:
            for icon_name, category_name in icons:
                table.row()

                table.cell(_("Actions"), css="buttons")
                delete_url = make_action_link([("mode", "icons"), ("_delete", icon_name)])
                html.icon_button(delete_url, _("Delete this Icon"), "delete")

                table.cell(_("Icon"), html.render_icon(icon_name), css="buttons")
                table.text_cell(_("Name"), icon_name)
                table.text_cell(_("Category"), IconSelector.category_alias(category_name))
