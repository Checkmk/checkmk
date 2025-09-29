# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import csv
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
                return row
        return None
