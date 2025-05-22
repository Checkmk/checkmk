#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The bulk import for hosts can be used to import multiple new hosts into a
single Setup folder. The hosts can either be provided by uploading a CSV file or
by pasting the contents of a CSV file into a textbox."""

import csv
import itertools
import operator
import time
import typing
import uuid
from collections.abc import Collection
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

import cmk.gui.pages
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
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
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.selection_id import SelectionId
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
from cmk.gui.watolib import bakery
from cmk.gui.watolib.host_attributes import host_attribute, HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_from_request
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode

# Was not able to get determine the type of csv._reader / _csv.reader
CSVReader = Any

ImportTuple = tuple[HostName, HostAttributes, None]


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeBulkImport)


class ModeBulkImport(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "bulk_import"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_hosts"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    def __init__(self) -> None:
        super().__init__()
        self._params: dict[str, Any] | None = None
        self._has_title_line = True

    @property
    def _upload_tmp_path(self) -> Path:
        return cmk.utils.paths.tmp_dir / "host-import"

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
        check_csrf_token()

        if transactions.transaction_valid():
            if request.has_var("_do_upload"):
                self._upload_csv_file()

            csv_reader = self._open_csv_file()

            if request.var("_do_import"):
                return self._import(csv_reader, debug=active_config.debug)
        return None

    def _file_path(self, file_id: str | None = None) -> Path:
        if file_id is None:
            file_id = request.get_str_input_mandatory("file_id")
        if not file_id.isalnum():
            raise MKUserError("file_id", _("The file_id has to be alphanumeric."))
        return self._upload_tmp_path / ("%s.csv" % file_id)

    # Upload the CSV file into a temporary directoy to make it available not only
    # for this request. It needs to be available during several potential "confirm"
    # steps and then through the upload step.
    def _upload_csv_file(self) -> None:
        self._upload_tmp_path.mkdir(mode=0o770, exist_ok=True, parents=True)

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

    def _get_custom_csv_dialect(self, delim: str) -> type[csv.Dialect]:
        class CustomCSVDialect(csv.excel):
            delimiter = delim

        return CustomCSVDialect

    def _open_csv_file(self) -> CSVReader:
        try:
            csv_file = self._file_path().open(encoding="utf-8")
        except OSError:
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

    def _import(self, csv_reader: CSVReader, *, debug: bool) -> ActionResult:
        def _emit_raw_rows(_reader: CSVReader) -> typing.Generator[dict, None, None]:
            if self._has_title_line:
                try:
                    next(_reader)  # skip header
                except StopIteration:
                    return

            def _check_duplicates(_names: list[str | None]) -> None:
                _attrs_seen = set()
                for _name in _names:
                    # "-" is the value set for "Don't import"
                    if _name != "-" and _name in _attrs_seen:
                        raise MKUserError(
                            None,
                            _(
                                'The attribute "%s" is assigned to multiple columns. '
                                "You can not populate one attribute from multiple columns. "
                                "The column to attribute associations need to be unique."
                            )
                            % _name,
                        )
                    _attrs_seen.add(_name)

            # Determine the used attributes once. We also check for duplicates only once.
            try:
                first_row = next(_reader)
            except StopIteration:
                return

            _attr_names = [request.var(f"attribute_{index}") for index in range(len(first_row))]
            _check_duplicates(_attr_names)
            yield dict(zip(_attr_names, first_row))

            for csv_row in _reader:
                if not csv_row:
                    continue  # skip empty lines

                yield dict(zip(_attr_names, csv_row))

        def _transform_and_validate_raw_rows(
            iterator: typing.Iterator[dict[str, str]],
        ) -> typing.Generator[ImportTuple, None, None]:
            """Here we transform each row into a tuple of HostName and HostAttributes and None.

            This format is directly compatible with Folder().create_hosts(...)

            Each attribute will be validated against it's corresponding ValueSpec.

            Example:
                Before:
                    [{'alias': 'foo', 'host_name': 'foo_server', 'dummy_attr': '5'}]

                After:
                    [('foo_server', {'alias': 'foo', 'dummy_attr': '5'}, None)]

            """
            hostname_valuespec = Hostname()

            class HostAttributeInstances(dict):
                def __missing__(self, key):
                    inst = host_attribute(key)
                    self[key] = inst
                    return inst

            host_attributes = HostAttributeInstances()

            for row_num, entry in enumerate(iterator):
                _host_name: HostName | None = None
                # keys are ordered in insert-first order, so we can derive col_num from the ordering
                for col_num, (attr_name, attr_value) in enumerate(
                    list(entry.items())
                ):  # iterate on copy
                    if attr_name == "host_name":
                        hostname_valuespec.validate_value(attr_value, "host")
                        # Remove host_name from attributes
                        del entry["host_name"]
                        _host_name = HostName(attr_value)
                    elif attr_name in ("-", ""):
                        # Don't import / No select
                        del entry[attr_name]
                    elif attr_name != "alias":
                        host_attribute_inst = host_attributes[attr_name]

                        if not attr_value.isascii():
                            raise MKUserError(
                                None,
                                _('Non-ASCII characters are not allowed in the attribute "%s".')
                                % attr_name,
                            )
                        try:
                            host_attribute_inst.validate_input(attr_value, "")
                        except MKUserError as exc:
                            raise MKUserError(
                                None,
                                _("Invalid value in column %d (%s) of row %d: %s")
                                % (col_num, attr_name, row_num, exc),
                            ) from exc

                if _host_name is None:
                    raise MKUserError(
                        None, _("The host name attribute needs to be assigned to a column.")
                    )

                yield _host_name, typing.cast(HostAttributes, entry), None

        raw_rows = _emit_raw_rows(csv_reader)
        host_attribute_tuples: typing.Iterator[ImportTuple] = _transform_and_validate_raw_rows(
            raw_rows
        )

        folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        imported_hosts, _failed_hosts, error_msgs = self._import_hosts_batched(
            host_attribute_tuples,
            folder=folder,
            batch_size=100,
        )

        bakery.try_bake_agents_for_hosts(imported_hosts, debug=debug)

        self._delete_csv_file()

        num_succeeded = len(imported_hosts)
        num_failed = len(error_msgs)

        # We select all imported ones.
        selected = [f"_c_{host_name}" for host_name in imported_hosts]

        folder_path = folder.path()
        if num_succeeded > 0 and request.var("do_service_detection") == "1":
            # Create a new selection for performing the bulk discovery
            user.set_rowselection(
                SelectionId.from_request(request),
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
                    selection=SelectionId.from_request(request),
                )
            )

        msg = _("Imported %d hosts into the current folder.") % num_succeeded
        if num_failed:
            msg += "<br><br>" + (_("%d errors occurred:") % num_failed)
            msg += "<ul>"
            for fail_msg in error_msgs:
                msg += "<li>%s</li>" % fail_msg
            msg += "</ul>"

        flash(msg)
        return redirect(mode_url("folder", folder=folder_path))

    def _import_hosts_batched(
        self,
        host_attribute_tuples: typing.Iterator[ImportTuple],
        *,
        folder: Folder,
        batch_size: int = 100,
    ) -> tuple[list[HostName], list[HostName], list[str]]:
        imported_hosts: list[HostName] = []
        failed_hosts: list[HostName] = []
        batch: tuple[ImportTuple, ...]

        index = 0
        fail_messages = []
        for batch in itertools.batched(host_attribute_tuples, batch_size):
            try:
                # NOTE
                # Folder.create_hosts will either import all of them, or no host at all. The
                # caught exceptions below will only trigger during the verification phase.
                folder.create_hosts(batch, pprint_value=active_config.wato_pprint_config)
                index += len(batch)
                # First column is host_name. Add all of them.
                imported_hosts.extend(map(operator.itemgetter(0), batch))
            except (MKAuthException, MKUserError, MKGeneralException):
                # We fall back to individual imports to determine the precise location of the error
                for entry in batch:
                    try:
                        folder.create_hosts([entry], pprint_value=active_config.wato_pprint_config)
                        index += 1
                        imported_hosts.append(entry[0])
                    except (MKAuthException, MKUserError, MKGeneralException) as exc:
                        failed_hosts.append(entry[0])
                        fail_messages.append(
                            _("Failed to create a host from line %d: %s") % (index, exc)
                        )

        return imported_hosts, failed_hosts, fail_messages

    def _delete_csv_file(self) -> None:
        self._file_path().unlink()

    def page(self) -> None:
        if not request.has_var("file_id"):
            self._upload_form()
        else:
            self._preview()

    def _upload_form(self) -> None:
        with html.form_context("upload", method="POST"):
            html.p(
                _(
                    "Using this page you can import several hosts at once into the chosen folder. You can "
                    "choose a CSV file from your workstation to be uploaded, paste a CSV files contents "
                    "into the text area or simply enter a list of host names (one per line) to the text area."
                )
            )

            self._vs_upload().render_input("_upload", None)
            html.hidden_fields()

    def _vs_upload(self):
        return Dictionary(
            elements=[
                (
                    "file",
                    UploadOrPasteTextFile(
                        elements=[],
                        allowed_extensions=[".csv"],
                        mime_types=["text/csv"],
                        title=_("Import hosts"),
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
            title=_("Import hosts"),
            optional_keys=[],
        )

    def _preview(self) -> None:
        with html.form_context("preview", method="POST"):
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
                    header = headers[col_num] if len(headers) > col_num else ""
                    table.cell(escape_to_html_permissive(header))
                    attribute_varname = "attribute_%d" % col_num
                    if request.var(attribute_varname):
                        attribute_method = request.get_ascii_input_mandatory(attribute_varname)
                    else:
                        attribute_method = self._try_detect_default_attribute(attributes, header)
                        request.del_var(attribute_varname)

                    html.dropdown(
                        "attribute_%d" % col_num,
                        attributes,
                        deflt=attribute_method,
                        autocomplete="off",
                    )

                # Render sample rows
                for row in rows:
                    table.row()
                    for cell in row:
                        table.cell(None, cell)

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
            ("host_name", _("Host name")),
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
