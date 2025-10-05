# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import csv
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import TextIO

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _


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
