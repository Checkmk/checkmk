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
"""The bulk import for hosts can be used to import multiple new hosts into a
single WATO folder. The hosts can either be provided by uploading a CSV file or
by pasting the contents of a CSV file into a textbox."""

import os
import csv
import time
from difflib import SequenceMatcher

import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.weblib as weblib
import cmk.gui.config as config
import cmk.gui.watolib as watolib
from cmk.gui.table import table_element
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.wato.pages.custom_attributes import ModeCustomHostAttrs

from cmk.gui.valuespec import (
    Hostname,
    Checkbox,
    Dictionary,
    FixedValue,
    TextAscii,
    UploadOrPasteTextFile,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)


@mode_registry.register
class ModeBulkImport(WatoMode):
    _upload_tmp_path = cmk.utils.paths.tmp_dir + "/host-import"

    @classmethod
    def name(cls):
        return "bulk_import"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]

    def __init__(self):
        super(ModeBulkImport, self).__init__()
        self._csv_reader = None
        self._params = None

    def title(self):
        return _("Bulk host import")

    def buttons(self):
        html.context_button(_("Abort"), watolib.folder_preserving_link([("mode", "folder")]),
                            "abort")
        if html.request.has_var("file_id"):
            html.context_button(_("Back"),
                                watolib.folder_preserving_link([("mode", "bulk_import")]), "back")

    def action(self):
        if html.transaction_valid():
            if html.request.has_var("_do_upload"):
                self._upload_csv_file()

            self._read_csv_file()

            if html.request.var("_do_import"):
                return self._import()

    def _file_path(self):
        file_id = html.request.var("file_id", "%s-%d" % (config.user.id, int(time.time())))
        return self._upload_tmp_path + "/%s.csv" % file_id

    # Upload the CSV file into a temporary directoy to make it available not only
    # for this request. It needs to be available during several potential "confirm"
    # steps and then through the upload step.
    def _upload_csv_file(self):
        store.makedirs(self._upload_tmp_path)

        self._cleanup_old_files()

        upload_info = self._vs_upload().from_html_vars("_upload")
        self._vs_upload().validate_value(upload_info, "_upload")
        _file_name, _mime_type, content = upload_info["file"]

        file_id = "%s-%d" % (config.user.id, int(time.time()))

        store.save_file(self._file_path(), content.encode("utf-8"))

        # make selections available to next page
        html.request.set_var("file_id", file_id)

        if upload_info["do_service_detection"]:
            html.request.set_var("do_service_detection", "1")

    def _cleanup_old_files(self):
        for f in os.listdir(self._upload_tmp_path):
            path = self._upload_tmp_path + "/" + f
            mtime = os.stat(path).st_mtime
            if mtime < time.time() - 3600:
                os.unlink(path)

    def _get_custom_csv_dialect(self, delim):
        class CustomCSVDialect(csv.excel):
            delimiter = delim

        return CustomCSVDialect()

    def _read_csv_file(self):
        try:
            csv_file = file(self._file_path())
        except IOError:
            raise MKUserError(
                None, _("Failed to read the previously uploaded CSV file. Please upload it again."))

        params = self._vs_parse_params().from_html_vars("_preview")
        self._vs_parse_params().validate_value(params, "_preview")
        self._params = params

        # try to detect the CSV format to be parsed
        if "field_delimiter" in params:
            csv_dialect = self._get_custom_csv_dialect(params["field_delimiter"])
        else:
            try:
                csv_dialect = csv.Sniffer().sniff(csv_file.read(2048), delimiters=",;\t:")
                csv_file.seek(0)
            except csv.Error as e:
                if "Could not determine delimiter" in str(e):
                    # Failed to detect the CSV files field delimiter character. Using ";" now. If
                    # you need another one, please specify it manually.
                    csv_dialect = self._get_custom_csv_dialect(";")
                    csv_file.seek(0)
                else:
                    raise

        # Save for preview in self.page()
        self._csv_reader = csv.reader(csv_file, csv_dialect)

    def _import(self):
        if self._params.get("has_title_line"):
            try:
                self._csv_reader.next()  # skip header
            except StopIteration:
                pass

        num_succeeded, num_failed = 0, 0
        fail_messages = []
        selected = []

        for row in self._csv_reader:
            if not row:
                continue  # skip empty lines

            host_name, attributes = self._get_host_info_from_row(row)
            try:
                watolib.Folder.current().create_hosts([(host_name, attributes, None)])
                selected.append('_c_%s' % host_name)
                num_succeeded += 1
            except Exception as e:
                fail_messages.append(
                    _("Failed to create a host from line %d: %s") % (self._csv_reader.line_num, e))
                num_failed += 1

        self._delete_csv_file()

        msg = _("Imported %d hosts into the current folder.") % num_succeeded
        if num_failed:
            msg += "<br><br>" + (_("%d errors occured:") % num_failed)
            msg += "<ul>"
            for fail_msg in fail_messages:
                msg += "<li>%s</li>" % fail_msg
            msg += "</ul>"

        if num_succeeded > 0 and html.request.var("do_service_detection") == "1":
            # Create a new selection for performing the bulk discovery
            weblib.set_rowselection('wato-folder-/' + watolib.Folder.current().path(), selected,
                                    'set')
            html.request.set_var('mode', 'bulkinventory')
            html.request.set_var('_bulk_inventory', '1')
            html.request.set_var('show_checkboxes', '1')
            return "bulkinventory"
        return "folder", msg

    def _delete_csv_file(self):
        os.unlink(self._file_path())

    def _get_host_info_from_row(self, row):
        host_name = None
        attributes = {}
        for col_num, value in enumerate(row):
            attribute = html.request.var("attribute_%d" % col_num)
            if attribute == "host_name":
                Hostname().validate_value(value, "host")
                host_name = value

            elif attribute and attribute != "-":
                if attribute in attributes:
                    raise MKUserError(
                        None,
                        _("The attribute \"%s\" is assigned to multiple columns. "
                          "You can not populate one attribute from multiple columns. "
                          "The column to attribute associations need to be unique.") % attribute)

                # FIXME: Couldn't we decode all attributes?
                if attribute == "alias":
                    attributes[attribute] = value.decode("utf-8")
                else:
                    try:
                        unicode(value)
                    except:
                        raise MKUserError(
                            None,
                            _("Non-ASCII characters are not allowed in the "
                              "attribute \"%s\".") % attribute)
                    attributes[attribute] = value

        if host_name is None:
            raise MKUserError(None, _("The host name attribute needs to be assigned to a column."))

        return host_name, attributes

    def page(self):
        if not html.request.has_var("file_id"):
            self._upload_form()
        else:
            self._preview()

    def _upload_form(self):
        html.begin_form("upload", method="POST")
        html.p(
            _("Using this page you can import several hosts at once into the choosen folder. You can "
              "choose a CSV file from your workstation to be uploaded, paste a CSV files contents "
              "into the textarea or simply enter a list of hostnames (one per line) to the textarea."
             ))

        self._vs_upload().render_input("_upload", None)
        html.hidden_fields()
        html.button("_do_upload", _("Upload"))
        html.end_form()

    def _vs_upload(self):
        return Dictionary(
            elements=[
                ("file",
                 UploadOrPasteTextFile(
                     title=_("Import Hosts"),
                     file_title=_("CSV File"),
                     allow_empty=False,
                     default_mode="upload",
                 )),
                ("do_service_detection", Checkbox(title=_("Perform automatic service discovery"),)),
            ],
            render="form",
            title=_("Import Hosts"),
            optional_keys=[],
        )

    def _preview(self):
        html.begin_form("preview", method="POST")
        self._preview_form()

        attributes = self._attribute_choices()

        self._read_csv_file()  # first line could be missing in situation of import error
        if not self._csv_reader:
            return  # don't try to show preview when CSV could not be read

        html.h2(_("Preview"))
        attribute_list = "<ul>%s</ul>" % "".join(
            ["<li>%s (%s)</li>" % a for a in attributes if a[0] is not None])
        html.help(
            _("This list shows you the first 10 rows from your CSV file in the way the import is "
              "currently parsing it. If the lines are not splitted correctly or the title line is "
              "not shown as title of the table, you may change the import settings above and try "
              "again.") + "<br><br>" +
            _("The first row below the titles contains fields to specify which column of the "
              "CSV file should be imported to which attribute of the created hosts. The import "
              "progress is trying to match the columns to attributes automatically by using the "
              "titles found in the title row (if you have some). "
              "If you use the correct titles, the attributes can be mapped automatically. The "
              "currently available attributes are:") + attribute_list +
            _("You can change these assignments according to your needs and then start the "
              "import by clicking on the <i>Import</i> button above."))

        # Wenn bei einem Host ein Fehler passiert, dann wird die Fehlermeldung zu dem Host angezeigt, so dass man sehen kann, was man anpassen muss.
        # Die problematischen Zeilen sollen angezeigt werden, so dass man diese als Block in ein neues CSV-File eintragen kann und dann diese Datei
        # erneut importieren kann.
        if self._params.get("has_title_line"):
            try:
                headers = list(self._csv_reader.next())
            except StopIteration:
                headers = []  # nope, there is no header
        else:
            headers = []

        rows = list(self._csv_reader)

        # Determine how many columns should be rendered by using the longest column
        num_columns = max([len(r) for r in [headers] + rows])

        with table_element(sortable=False,
                           searchable=False,
                           omit_headers=not self._params.get("has_title_line")) as table:

            # Render attribute selection fields
            table.row()
            for col_num in range(num_columns):
                header = headers[col_num] if len(headers) > col_num else None
                table.cell(html.render_text(header))
                attribute_varname = "attribute_%d" % col_num
                if html.request.var(attribute_varname):
                    attribute_method = html.request.var("attribute_varname")
                else:
                    attribute_method = self._try_detect_default_attribute(attributes, header)
                    html.request.del_var(attribute_varname)

                html.dropdown("attribute_%d" % col_num,
                              attributes,
                              deflt=attribute_method,
                              autocomplete="off")

            # Render sample rows
            for row in rows:
                table.row()
                for cell in row:
                    table.cell(None, html.render_text(cell))

        html.end_form()

    def _preview_form(self):
        if self._params is not None:
            params = self._params
        else:
            params = self._vs_parse_params().default_value()
        self._vs_parse_params().render_input("_preview", params)
        html.hidden_fields()
        html.button("_do_preview", _("Update preview"))
        html.button("_do_import", _("Import"))

    def _vs_parse_params(self):
        return Dictionary(
            elements=[
                ("field_delimiter",
                 TextAscii(
                     title=_("Set field delimiter"),
                     default_value=";",
                     size=1,
                     allow_empty=False,
                 )),
                ("has_title_line",
                 FixedValue(
                     True,
                     title=_("Has title line"),
                     totext=_("The first line in the file contains titles."),
                 )),
            ],
            render="form",
            title=_("File Parsing Settings"),
            default_keys=["has_title_line"],
        )

    def _attribute_choices(self):
        attributes = [
            (None, _("(please select)")),
            ("-", _("Don't import")),
            ("host_name", _("Hostname")),
            ("alias", _("Alias")),
            ("site", _("Monitored on site")),
            ("ipaddress", _("IPv4 Address")),
            ("ipv6address", _("IPv6 Address")),
            ("snmp_community", _("SNMP Community")),
        ]

        # Add tag groups
        for tag_group in config.tags.tag_groups:
            attributes.append(("tag_" + tag_group.id, _("Tag: %s") % tag_group.title))

        # Add custom attributes
        for entry in ModeCustomHostAttrs().get_attributes():
            name = entry['name']
            attributes.append((name, _("Custom variable: %s") % name))

        return attributes

    # Try to detect the host attribute to choose for this column based on the header
    # of this column (if there is some).
    def _try_detect_default_attribute(self, attributes, header):
        if header is None:
            return ""

        def similarity(a, b):
            return SequenceMatcher(None, a, b).ratio()

        highscore = 0.0
        best_key = ""
        for key, title in attributes:
            if key is not None:
                key_match_score = similarity(key, header)
                title_match_score = similarity(title, header)
                score = key_match_score if key_match_score > title_match_score else title_match_score

                if score > 0.6 and score > highscore:
                    best_key = key
                    highscore = score

        return best_key
