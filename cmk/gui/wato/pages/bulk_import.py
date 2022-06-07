#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The bulk import for hosts can be used to import multiple new hosts into a
single WATO folder. The hosts can either be provided by uploading a CSV file or
by pasting the contents of a CSV file into a textbox."""

import csv
import time
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Collection, Dict, Optional, Type

import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.watolib.bakery as bakery
import cmk.gui.weblib as weblib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_simple_form_page_menu,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils import flash, mode_registry, mode_url, redirect, WatoMode
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    FixedValue,
    Hostname,
    TextInput,
    UploadOrPasteTextFile,
)
from cmk.gui.wato.pages.custom_attributes import ModeCustomHostAttrs
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.host_attributes import host_attribute_registry
from cmk.gui.watolib.hosts_and_folders import Folder

# Was not able to get determine the type of csv._reader / _csv.reader
CSVReader = Any


@mode_registry.register
class ModeBulkImport(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "bulk_import"

    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return ["hosts", "manage_hosts"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def __init__(self) -> None:
        super().__init__()
        self._params: Optional[Dict[str, Any]] = None
        self._has_title_line = True

    @property
    def _upload_tmp_path(self) -> Path:
        return Path(cmk.utils.paths.tmp_dir) / "host-import"

    def title(self) -> str:
        return _("Bulk host import")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if not request.has_var("file_id"):
            return make_simple_form_page_menu(
                _("Hosts"),
                breadcrumb,
                form_name="upload",
                button_name="_do_upload",
                save_title=_("Upload"),
            )

        # preview phase, after first upload
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Actions"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Update preview"),
                                    icon_name="update",
                                    item=make_form_submit_link("preview", "_do_preview"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Import"),
                                    icon_name="save",
                                    item=make_form_submit_link("preview", "_do_import"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        if transactions.transaction_valid():
            if request.has_var("_do_upload"):
                self._upload_csv_file()

            csv_reader = self._open_csv_file()

            if request.var("_do_import"):
                return self._import(csv_reader)
        return None

    def _file_path(self, file_id: Optional[str] = None) -> Path:
        if file_id is None:
            file_id = request.get_str_input_mandatory("file_id")
        if not file_id.isalnum():
            raise MKUserError("file_id", _("The file_id has to be alphanumeric."))
        return self._upload_tmp_path / ("%s.csv" % file_id)

    # Upload the CSV file into a temporary directoy to make it available not only
    # for this request. It needs to be available during several potential "confirm"
    # steps and then through the upload step.
    def _upload_csv_file(self) -> None:
        store.makedirs(self._upload_tmp_path)

        self._cleanup_old_files()

        upload_info = self._vs_upload().from_html_vars("_upload")
        self._vs_upload().validate_value(upload_info, "_upload")

        file_id = uuid.uuid4().hex

        store.save_text_to_file(self._file_path(file_id=file_id), upload_info["file"])

        # make selections available to next page
        request.set_var("file_id", file_id)

        if upload_info["do_service_detection"]:
            request.set_var("do_service_detection", "1")

    def _cleanup_old_files(self) -> None:
        for path in self._upload_tmp_path.iterdir():
            mtime = path.stat().st_mtime
            if mtime < time.time() - 3600:
                path.unlink()

    def _get_custom_csv_dialect(self, delim: str) -> Type[csv.Dialect]:
        class CustomCSVDialect(csv.excel):
            delimiter = delim

        return CustomCSVDialect

    def _open_csv_file(self) -> CSVReader:
        try:
            csv_file = self._file_path().open(encoding="utf-8")
        except IOError:
            raise MKUserError(
                None, _("Failed to read the previously uploaded CSV file. Please upload it again.")
            )

        if list(request.itervars(prefix="_preview")):
            params = self._vs_parse_params().from_html_vars("_preview")
        else:
            params = {
                "has_title_line": True,
            }

        self._vs_parse_params().validate_value(params, "_preview")
        self._params = params
        assert self._params is not None
        self._has_title_line = self._params.get("has_title_line", False)

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

        return csv.reader(csv_file, csv_dialect)

    def _import(self, csv_reader: CSVReader) -> ActionResult:
        if self._has_title_line:
            try:
                next(csv_reader)  # skip header
            except StopIteration:
                pass

        num_succeeded, num_failed = 0, 0
        fail_messages = []
        selected = []
        imported_hosts = []

        for row_num, row in enumerate(csv_reader):
            if not row:
                continue  # skip empty lines

            host_name, attributes = self._get_host_info_from_row(row, row_num)
            try:
                Folder.current().create_hosts(
                    [(host_name, attributes, None)],
                    bake_hosts=False,
                )
                imported_hosts.append(host_name)
                selected.append("_c_%s" % host_name)
                num_succeeded += 1
            except Exception as e:
                fail_messages.append(
                    _("Failed to create a host from line %d: %s") % (csv_reader.line_num, e)
                )
                num_failed += 1

        bakery.try_bake_agents_for_hosts(imported_hosts)

        self._delete_csv_file()

        msg = _("Imported %d hosts into the current folder.") % num_succeeded
        if num_failed:
            msg += "<br><br>" + (_("%d errors occured:") % num_failed)
            msg += "<ul>"
            for fail_msg in fail_messages:
                msg += "<li>%s</li>" % fail_msg
            msg += "</ul>"

        folder_path = Folder.current().path()
        if num_succeeded > 0 and request.var("do_service_detection") == "1":
            # Create a new selection for performing the bulk discovery
            user.set_rowselection(
                weblib.selection_id(),
                "wato-folder-/" + folder_path,
                selected,
                "set",
            )
            return redirect(
                mode_url(
                    "bulkinventory",
                    _bulk_inventory="1",
                    show_checkboxes="1",
                    folder=folder_path,
                    selection=weblib.selection_id(),
                )
            )
        flash(msg)
        return redirect(mode_url("folder", folder=folder_path))

    def _delete_csv_file(self) -> None:
        self._file_path().unlink()

    def _get_host_info_from_row(self, row, row_num):
        host_name = None
        attributes: Dict[str, str] = {}
        for col_num, value in enumerate(row):
            if not value:
                continue

            attribute = request.var("attribute_%d" % col_num)
            if attribute == "host_name":
                Hostname().validate_value(value, "host")
                host_name = value

            elif attribute and attribute != "-":
                if attribute in attributes:
                    raise MKUserError(
                        None,
                        _(
                            'The attribute "%s" is assigned to multiple columns. '
                            "You can not populate one attribute from multiple columns. "
                            "The column to attribute associations need to be unique."
                        )
                        % attribute,
                    )

                attr = host_attribute_registry[attribute]()

                # TODO: The value handling here is incorrect. The correct way would be to use the
                # host attributes from_html_vars and validate_input, just like collect_attributes()
                # from cmk/gui/watolib/host_attributes.py is doing it.
                # The problem here is that we get the value in a different way (from row instead of
                # HTTP request vars) which from_html_vars can not work with.

                if attribute == "alias":
                    attributes[attribute] = value
                else:
                    if not value.isascii():
                        raise MKUserError(
                            None,
                            _('Non-ASCII characters are not allowed in the attribute "%s".')
                            % attribute,
                        )

                    try:
                        attr.validate_input(value, "")
                    except MKUserError as e:
                        raise MKUserError(
                            None,
                            _("Invalid value in column %d (%s) of row %d: %s")
                            % (col_num, attribute, row_num, e),
                        )

                    attributes[attribute] = value

        if host_name is None:
            raise MKUserError(None, _("The host name attribute needs to be assigned to a column."))

        return host_name, attributes

    def page(self) -> None:
        if not request.has_var("file_id"):
            self._upload_form()
        else:
            self._preview()

    def _upload_form(self) -> None:
        html.begin_form("upload", method="POST")
        html.p(
            _(
                "Using this page you can import several hosts at once into the choosen folder. You can "
                "choose a CSV file from your workstation to be uploaded, paste a CSV files contents "
                "into the textarea or simply enter a list of hostnames (one per line) to the textarea."
            )
        )

        self._vs_upload().render_input("_upload", None)
        html.hidden_fields()
        html.end_form()

    def _vs_upload(self):
        return Dictionary(
            elements=[
                (
                    "file",
                    UploadOrPasteTextFile(
                        elements=[],
                        title=_("Import Hosts"),
                        file_title=_("CSV File"),
                    ),
                ),
                (
                    "do_service_detection",
                    Checkbox(
                        title=_("Perform automatic service discovery"),
                    ),
                ),
            ],
            render="form",
            title=_("Import Hosts"),
            optional_keys=[],
        )

    def _preview(self) -> None:
        html.begin_form("preview", method="POST")
        self._preview_form()

        attributes = self._attribute_choices()

        # first line could be missing in situation of import error
        csv_reader = self._open_csv_file()
        if not csv_reader:
            return  # don't try to show preview when CSV could not be read

        html.h2(_("Preview"))
        attribute_list = "<ul>%s</ul>" % "".join(
            ["<li>%s (%s)</li>" % a for a in attributes if a[0] is not None]
        )
        html.help(
            _(
                "This list shows you the first 10 rows from your CSV file in the way the import is "
                "currently parsing it. If the lines are not splitted correctly or the title line is "
                "not shown as title of the table, you may change the import settings above and try "
                "again."
            )
            + "<br><br>"
            + _(
                "The first row below the titles contains fields to specify which column of the "
                "CSV file should be imported to which attribute of the created hosts. The import "
                "progress is trying to match the columns to attributes automatically by using the "
                "titles found in the title row (if you have some). "
                "If you use the correct titles, the attributes can be mapped automatically. The "
                "currently available attributes are:"
            )
            + attribute_list
            + _(
                "You can change these assignments according to your needs and then start the "
                "import by clicking on the <i>Import</i> button above."
            )
        )

        # Wenn bei einem Host ein Fehler passiert, dann wird die Fehlermeldung zu dem Host angezeigt, so dass man sehen kann, was man anpassen muss.
        # Die problematischen Zeilen sollen angezeigt werden, so dass man diese als Block in ein neues CSV-File eintragen kann und dann diese Datei
        # erneut importieren kann.
        if self._has_title_line:
            try:
                headers = list(next(csv_reader))
            except StopIteration:
                headers = []  # nope, there is no header
        else:
            headers = []

        rows = list(csv_reader)

        # Determine how many columns should be rendered by using the longest column
        num_columns = max(len(r) for r in [headers] + rows)

        with table_element(
            sortable=False, searchable=False, omit_headers=not self._has_title_line
        ) as table:

            # Render attribute selection fields
            table.row()
            for col_num in range(num_columns):
                header = headers[col_num] if len(headers) > col_num else None
                table.cell(escape_to_html_permissive(header))
                attribute_varname = "attribute_%d" % col_num
                if request.var(attribute_varname):
                    attribute_method = request.get_ascii_input_mandatory(attribute_varname)
                else:
                    attribute_method = self._try_detect_default_attribute(attributes, header)
                    request.del_var(attribute_varname)

                html.dropdown(
                    "attribute_%d" % col_num, attributes, deflt=attribute_method, autocomplete="off"
                )

            # Render sample rows
            for row in rows:
                table.row()
                for cell in row:
                    table.cell(None, cell)

        html.end_form()

    def _preview_form(self) -> None:
        if self._params is not None:
            params = self._params
        else:
            params = self._vs_parse_params().default_value()
        self._vs_parse_params().render_input("_preview", params)
        html.hidden_fields()

    def _vs_parse_params(self):
        return Dictionary(
            elements=[
                (
                    "field_delimiter",
                    TextInput(
                        title=_("Set field delimiter"),
                        default_value=";",
                        size=1,
                        allow_empty=False,
                    ),
                ),
                (
                    "has_title_line",
                    FixedValue(
                        value=True,
                        title=_("Has title line"),
                        totext=_("The first line in the file contains titles."),
                    ),
                ),
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
            ("ipaddress", _("IPv4 address")),
            ("ipv6address", _("IPv6 address")),
            ("snmp_community", _("SNMP community")),
        ]

        # Add tag groups
        for tag_group in active_config.tags.tag_groups:
            attributes.append(("tag_" + tag_group.id, _("Tag: %s") % tag_group.title))

        # Add custom attributes
        for entry in ModeCustomHostAttrs().get_attributes():
            name = entry["name"]
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
                score = (
                    key_match_score if key_match_score > title_match_score else title_match_score
                )

                if score > 0.6 and score > highscore:
                    best_key = key
                    highscore = score

        return best_key
