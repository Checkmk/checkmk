#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The bulk import for hosts can be used to import multiple new hosts into a
single Setup folder. The hosts can either be provided by uploading a CSV file or
by pasting the contents of a CSV file into a textbox."""

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import csv
import itertools
import operator
import time
import typing
import uuid
from collections.abc import Collection, Iterator, Mapping, Sequence
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, TextIO

import cmk.gui.pages
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
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
from cmk.gui.type_defs import (
    ActionResult,
    Choices,
    CustomHostAttrSpec,
    PermissionName,
)
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
from cmk.gui.watolib.host_attributes import ABCHostAttribute, all_host_attributes, HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_from_request
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.utils.tags import TagGroup

ImportTuple = tuple[HostName, HostAttributes, None]


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeBulkImport)


def _prevent_reused_attr_names(attr_names: Sequence[str | None]) -> None:
    """
    A user might try to assign two different columns to be the same attribute
    e.g. "host name", which doesn't make sense. Prevent that here by checking
    the list of attribute names selected by the user and ensuring they are
    all unique, throwing an exception if not.
    """
    attrs_seen = set()
    for name in attr_names:
        # "-" is the value set for "Don't import"
        if name != "-" and name in attrs_seen:
            raise MKUserError(
                None,
                _(
                    'The attribute "%s" is assigned to multiple columns. '
                    "You can not populate one attribute from multiple columns. "
                    "The column-to-attribute associations need to be unique."
                )
                % name,
            )
        attrs_seen.add(name)


def _attribute_choices(
    tag_groups: Sequence[TagGroup],
    custom_host_attrs: Sequence[CustomHostAttrSpec],
) -> Choices:
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
    for tag_group in tag_groups:
        attributes.append(("tag_" + tag_group.id, _("Tag: %s") % tag_group.title))

    # Add custom attributes
    for entry in custom_host_attrs:
        name = entry["name"]
        attributes.append((name, _("Custom variable: %s") % name))

    return attributes


def _detect_attribute(attributes: Choices, header: str) -> str:
    """
    Given a 'Choices' of possible host attributes, and assuming there is a
    title line in the CSV, try to match the given title (for a particular
    column) with the attribute key most likely related to it.
    """

    if not header:
        return ""

    highscore = 0.0
    best_key = ""
    for key, title in attributes:
        if key is not None:
            key_match_score = SequenceMatcher(None, key, header).ratio()
            title_match_score = SequenceMatcher(None, title, header).ratio()
            score = key_match_score if key_match_score > title_match_score else title_match_score

            if score > 0.6 and score > highscore:
                best_key = key
                highscore = score

    return best_key


def _host_rows_to_bulk(
    iterator: typing.Iterator[dict[str, str]],
    host_attributes: Mapping[str, ABCHostAttribute],
) -> typing.Generator[ImportTuple, None, None]:
    """Here we transform each row into a tuple of HostName and HostAttributes and None.

    This format is directly compatible with Folder().create_hosts(...)

    Each attribute will be validated against its corresponding ValueSpec.

    Example:
        Before:
            [{'alias': 'foo', 'host_name': 'foo_server', 'dummy_attr': '5'}]

        After:
            [('foo_server', {'alias': 'foo', 'dummy_attr': '5'}, None)]

    """
    hostname_valuespec = Hostname()

    for row_num, entry in enumerate(iterator):
        entry = entry.copy()  # Don't operate on the original
        _host_name: HostName | None = None
        # keys are ordered in insert-first order, so we can derive col_num from the ordering
        for col_num, (attr_name, attr_value) in enumerate(list(entry.items())):  # iterate on copy
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
            raise MKUserError(None, _("The host name attribute needs to be assigned to a column."))

        yield _host_name, typing.cast(HostAttributes, entry), None


def _get_custom_csv_dialect(delim: str) -> type[csv.Dialect]:
    class CustomCSVDialect(csv.excel):
        delimiter = delim

    return CustomCSVDialect


def get_handle_for_csv(path: Path) -> TextIO:
    """
    Public function to attempt to open a CSV file with the correct encoding,
    from the path given.
    """
    try:
        return path.open(encoding="utf-8")
    except OSError:
        raise MKUserError(
            None, _("Failed to read the previously uploaded CSV file. Please upload it again.")
        )


class CSVBulkImport:
    def __init__(self, handle: TextIO, has_title_line: bool, delimiter: str | None = None):
        self._handle = handle  # Take a handle instead of a Path for easier testing
        self._dialect = self._determine_dialect(delimiter)
        self._reader = csv.reader(self._handle, self._dialect)

        self._num_fields: int | None = None
        self._num_fields = self.row_length

        self._has_title_line = has_title_line
        self._title_row: list[str] | None = None
        if self._has_title_line:
            self._title_row = self.title_row

    def _determine_dialect(self, delimiter: str | None) -> type[csv.Dialect]:
        """
        Attempt to return a csv.Dialect that works to parse the file.

        Called only by the constructor: Calling this method later might manipulate the file cursor
        and cause the instance to lose track of where it was in the file.
        """
        if delimiter is not None:
            return _get_custom_csv_dialect(delimiter)

        try:
            dialect = csv.Sniffer().sniff(self._handle.read(2048), delimiters=",;\t:")
        except csv.Error as e:
            if "Could not determine delimiter" in str(e):
                # Default to splitting on ;
                dialect = _get_custom_csv_dialect(";")
            else:
                raise

        self._handle.seek(0)
        return dialect

    def skip_to_and_return_next_row(self) -> list[str] | None:
        """
        Skip ahead to the next row that has data in it (if any). If there are no remaining
        rows with data, return None.
        """
        for row in self._reader:
            if row:
                # If there are *only* spaces on the line, skip it
                if len(row) == 1 and row[0].strip() == "":
                    continue

                # This very function is called to determine the row length.
                # In that case, self._num_fields won't be set yet.
                if self._num_fields is not None and len(row) != self.row_length:
                    raise MKUserError(
                        None,
                        _(
                            "All rows in the CSV file must have the same number of columns. "
                            "The following row had a different number of columns than the first "
                            "row (or the title row, if one is present): %s"
                        )
                        % repr(row),
                    )
                return row
        return None

    def rows(self) -> Iterator[list[str]]:
        while (next_row := self.skip_to_and_return_next_row()) is not None:
            yield next_row
        return

    def __iter__(self) -> Iterator[list[str]]:
        yield from self.rows()

    @property
    def row_length(self) -> int:
        if self._num_fields is not None:
            return self._num_fields

        current_pos = self._handle.tell()
        next_row = self.skip_to_and_return_next_row() or []
        self._handle.seek(current_pos)
        return len(next_row)

    @property
    def title_row(self) -> list[str] | None:
        """
        Return the title row, if one exists, taking care to only ever advance the reader
        cursor once, even if called multiple times.
        """
        if not self._has_title_line:
            # If we aren't expecting a title line and we are called anyway, do not
            # advance the reader cursor.
            return None

        if self._title_row is not None:
            # If we've already established the title row, then just return it.
            return self._title_row

        # TODO: Consider throwing if there is no next row
        return self.skip_to_and_return_next_row()

    @property
    def has_title_line(self) -> bool:
        return self._has_title_line

    def rows_as_dict(self, attr_names: Sequence[str]) -> Iterator[dict[str, str]]:
        """
        Yield each row rendered as a dictionary with keys being the names given in attr_names
        and values being the fields from the CSV.

        In other words:
        Given attr_names=["host_name", "ipaddress"]

        ..and a row like:
        "server01,192.168.100.1"

        ...we would yield:
        {"host_name": "server01", "ipaddress": "192.168.100.1"}.

        Raises an exception if the number of attr_names differs from the number of fields.
        """
        if len(attr_names) != self.row_length:
            raise ValueError(
                f"Got {len(attr_names)} attribute names, but row length is {self.row_length}"
            )

        while (row := self.skip_to_and_return_next_row()) is not None:
            yield dict(zip(attr_names, row))


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

    @property
    def _upload_tmp_path(self) -> Path:
        return cmk.utils.paths.tmp_dir / "host-import"

    def title(self) -> str:
        return _("Bulk host import")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
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

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if transactions.transaction_valid():
            if request.has_var("_do_upload"):
                self._upload_csv_file()

            has_title_line = self.params.get("has_title_line", False)
            delimiter = self.params.get("field_delimiter")
            csv_bulk_import = self._open_csv_file(has_title_line, delimiter)

            if request.var("_do_import"):
                return self._import(
                    csv_bulk_import,
                    host_attributes=all_host_attributes(
                        config.wato_host_attrs, config.tags.get_tag_groups_by_topic()
                    ),
                    debug=config.debug,
                    pprint_value=config.wato_pprint_config,
                    use_git=config.wato_use_git,
                )
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

    @property
    def params(self) -> dict[str, Any]:
        if self._params is None:
            self._params = self.validate_params()
        return self._params

    def validate_params(self) -> dict[str, Any]:
        vs_parse_params = self._vs_parse_params()

        # If the request has any _preview* vars at all, populate the ValueSpec instance with them.
        # Otherwise, use the defaults from the ValueSpec itself.
        if any(True for _ in request.itervars(prefix="_preview")):
            params = vs_parse_params.from_html_vars("_preview")
        else:
            params = self._vs_parse_params().default_value()

        vs_parse_params.validate_value(params, "_preview")
        return params

    def _open_csv_file(self, has_title_line: bool, delimiter: str | None) -> CSVBulkImport:
        handle = get_handle_for_csv(self._file_path())
        return CSVBulkImport(handle, has_title_line, delimiter)

    def _import(
        self,
        csv_bulk_import: CSVBulkImport,
        host_attributes: Mapping[str, ABCHostAttribute],
        *,
        debug: bool,
        pprint_value: bool,
        use_git: bool,
    ) -> ActionResult:
        # The attribute names will come as request variables stored at attribute_0...attribute_n
        # where n is, in theory, the row length - 1. And, in theory, they should always exist, even
        # if they are the empty string. 'None' would be weird, likely the user manually modified
        # the form and deleted the field. In that case, rows_as_dict() would raise ValueError.
        attr_names: list[str] = [
            name
            for index in range(csv_bulk_import.row_length)
            if (name := request.var(f"attribute_{index}")) is not None
        ]
        raw_rows = csv_bulk_import.rows_as_dict(attr_names)
        host_attribute_tuples: typing.Iterator[ImportTuple] = _host_rows_to_bulk(
            raw_rows, host_attributes
        )

        folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        imported_hosts, _failed_hosts, error_msgs = self._import_hosts_batched(
            host_attribute_tuples,
            folder=folder,
            batch_size=100,
            pprint_value=pprint_value,
            use_git=use_git,
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
        pprint_value: bool,
        use_git: bool,
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
                folder.create_hosts(batch, pprint_value=pprint_value, use_git=use_git)
                index += len(batch)
                # First column is host_name. Add all of them.
                imported_hosts.extend(map(operator.itemgetter(0), batch))
            except (MKAuthException, MKUserError, MKGeneralException):
                # We fall back to individual imports to determine the precise location of the error
                for entry in batch:
                    try:
                        folder.create_hosts([entry], pprint_value=pprint_value, use_git=use_git)
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

    def page(self, config: Config) -> None:
        if not request.has_var("file_id"):
            self._upload_form()
        else:
            self._preview(config.tags.tag_groups)

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

    def _preview(self, tag_groups: Sequence[TagGroup]) -> None:
        with html.form_context("preview", method="POST"):
            self._preview_form()

            custom_host_attrs = ModeCustomHostAttrs().get_attributes()
            attributes = _attribute_choices(tag_groups, custom_host_attrs)

            # first line could be missing in situation of import error
            has_title_line = self.params.get("has_title_line", False)
            delimiter = self.params.get("field_delimiter")
            csv_bulk_import = self._open_csv_file(has_title_line, delimiter)

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

            headers: list[str] = csv_bulk_import.title_row or []

            # 2.5+: We explicitly assume a well-formed CSV with consistent column lengths
            # and CSVBulkImport will raise if ever asked to produce a row (e.g. from rows_as_dict())
            # with a number of columns different from the first row (or title row if it exists).
            #
            # In <2.5, we would silently drop extra columns on import.
            num_columns = csv_bulk_import.row_length

            with table_element(
                sortable=False, searchable=False, omit_headers=not csv_bulk_import.has_title_line
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
                        attribute_method = _detect_attribute(attributes, header)
                        request.del_var(attribute_varname)

                    html.dropdown(
                        "attribute_%d" % col_num,
                        attributes,
                        deflt=attribute_method,
                        autocomplete="off",
                    )

                # Render sample rows
                for row in csv_bulk_import:
                    table.row()
                    for cell in row:
                        table.cell(None, cell)

    def _preview_form(self) -> None:
        self._vs_parse_params().render_input("_preview", self.params)
        html.hidden_fields()

    def _vs_parse_params(self) -> Dictionary:
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
