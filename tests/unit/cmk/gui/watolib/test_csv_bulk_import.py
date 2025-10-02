# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.csv_bulk_import import CSVBulkImport, get_handle_for_csv

CSV_NO_TITLE_LINE = """
server01,192.168.1.101
server02,192.168.1.102
server03,192.168.1.103
""".strip()

CSV_WITH_SEMICOLONS = CSV_NO_TITLE_LINE.replace(",", ";")

# Multiple characters that "could" be a delimiter
CSV_MULTI_DELIM = """
2001:16c2:a123:2345:2ac4:c3e:6794:85cc,server01
2001:16c2:a123:2345:2ac4:c3e:6794:85cd,server02
2001:16c2:a123:2345:2ac4:c3e:6794:85ce,server03
""".strip()

CSV_WITH_TITLE_LINE = "hostname,ipaddr\n" + CSV_NO_TITLE_LINE
CSV_WITH_TITLE_LINE_BLANK_LINES_BEFORE = ("\n" * 10) + CSV_WITH_TITLE_LINE

CSV_WITH_ONE_LINE_NO_TITLE_LINE = "server01,192.168.1.101"

# An edge-case sample where dialect sniffing doesn't work because the first 2048
# characters don't have one of the default delimiters in them.
EDGE_CASE_CSV_CANT_SNIFF = ("\n" * 2048) + CSV_NO_TITLE_LINE

# An edge-case sample with scattered newlines throughout the rows
EDGE_CASE_CSV_SCATTERED_NEWLINES_WITH_TITLE_LINE = """


hostname,ipaddr

server01,192.168.1.101


server02,192.168.1.102
server03,192.168.1.103

"""

EDGE_CASE_CSV_SCATTERED_NEWLINES_NO_TITLE_LINE = """


server01,192.168.1.101


server02,192.168.1.102
server03,192.168.1.103

"""


@pytest.mark.parametrize(
    "sample, delimiter, expected_delimeter",
    [
        pytest.param(
            CSV_NO_TITLE_LINE,
            ",",
            ",",
            id="normal CSV file with specified delim",
        ),
        pytest.param(
            CSV_NO_TITLE_LINE,
            None,
            ",",
            id="normal CSV file, no delim given",
        ),
        pytest.param(
            CSV_WITH_SEMICOLONS,
            None,
            ";",
            id="CSV with semicolons, delim not specified",
        ),
        pytest.param(
            EDGE_CASE_CSV_CANT_SNIFF,
            None,
            ";",
            id="CSV with no delim in first 2048 bytes falls back to semicolon",
        ),
        pytest.param(
            CSV_MULTI_DELIM,
            None,
            ",",
            id="CSV with multiple chars that could be a delim prefers comma",
        ),
        pytest.param(
            "",
            None,
            ";",
            id="Empty CSV defaults to semicolon (no crash)",
        ),
    ],
)
def test_determine_dialect(sample: str, delimiter: str, expected_delimeter: str) -> None:
    handle = StringIO(sample)
    assert (
        CSVBulkImport(handle=handle, has_title_line=False, delimiter=delimiter)._dialect.delimiter
        == expected_delimeter
    )


def test_get_handle_for_csv() -> None:
    with pytest.raises(MKUserError):
        get_handle_for_csv(
            Path("/this/path/does/not/exist/hopefully/otherwise/this/test/will/really/fail.csv")
        )


@pytest.mark.parametrize(
    "sample, expected_first_row, expected_second_row",
    [
        pytest.param(
            CSV_NO_TITLE_LINE,
            ["server01", "192.168.1.101"],
            ["server02", "192.168.1.102"],
            id="CSV file with no title line",
        ),
        pytest.param(
            EDGE_CASE_CSV_SCATTERED_NEWLINES_NO_TITLE_LINE,
            ["server01", "192.168.1.101"],
            ["server02", "192.168.1.102"],
            id="CSV file with scattered newlines",
        ),
        pytest.param(
            CSV_WITH_ONE_LINE_NO_TITLE_LINE,
            ["server01", "192.168.1.101"],
            None,
            id="CSV file with only one line (no title line)",
        ),
        pytest.param(
            "",
            None,
            None,
            id="CSV file no lines",
        ),
    ],
)
def test_skip_to_and_return_next_row(
    sample: str,
    expected_first_row: Sequence[str],
    expected_second_row: Sequence[str],
) -> None:
    handle = StringIO(sample)
    cbi = CSVBulkImport(handle=handle, has_title_line=False)
    assert cbi.skip_to_and_return_next_row() == expected_first_row
    assert cbi.skip_to_and_return_next_row() == expected_second_row


@pytest.mark.parametrize(
    "sample, has_title_line, expected_title_row, expected_next_row",
    [
        pytest.param(
            CSV_NO_TITLE_LINE,
            False,
            None,
            ["server01", "192.168.1.101"],
            id="CSV file with no title line",
        ),
        pytest.param(
            CSV_WITH_TITLE_LINE,
            True,
            ["hostname", "ipaddr"],
            ["server01", "192.168.1.101"],
            id="CSV file with title line",
        ),
        pytest.param(
            EDGE_CASE_CSV_SCATTERED_NEWLINES_WITH_TITLE_LINE,
            True,
            ["hostname", "ipaddr"],
            ["server01", "192.168.1.101"],
            id="CSV file with scattered newlines and title line",
        ),
        pytest.param(
            EDGE_CASE_CSV_SCATTERED_NEWLINES_NO_TITLE_LINE,
            False,
            None,
            ["server01", "192.168.1.101"],
            id="CSV file with scattered newlines and no title line",
        ),
    ],
)
def test_title_row(
    sample: str,
    has_title_line: bool,
    expected_title_row: Sequence[str],
    expected_next_row: Sequence[str],
) -> None:
    handle = StringIO(sample)
    cbi = CSVBulkImport(handle=handle, has_title_line=has_title_line)
    # We call title_row() twice to ensure the cursor only advances once
    assert cbi.title_row == expected_title_row
    assert cbi.title_row == expected_title_row
    assert cbi.skip_to_and_return_next_row() == expected_next_row


@pytest.mark.parametrize(
    "sample, has_title_line, attr_names, expected_result",
    [
        pytest.param(
            CSV_NO_TITLE_LINE,
            False,
            ["host_name", "ipaddress"],
            [
                {"host_name": "server01", "ipaddress": "192.168.1.101"},
                {"host_name": "server02", "ipaddress": "192.168.1.102"},
                {"host_name": "server03", "ipaddress": "192.168.1.103"},
            ],
            id="CSV, no title line, green path",
        ),
        pytest.param(
            CSV_WITH_TITLE_LINE,
            True,
            ["host_name", "ipaddress"],
            [
                {"host_name": "server01", "ipaddress": "192.168.1.101"},
                {"host_name": "server02", "ipaddress": "192.168.1.102"},
                {"host_name": "server03", "ipaddress": "192.168.1.103"},
            ],
            id="CSV with title line, green path",
        ),
    ],
)
def test_next_row_as_dict(
    sample: str,
    has_title_line: bool,
    attr_names: Sequence[str],
    expected_result: Sequence[Mapping[str, str]],
) -> None:
    handle = StringIO(sample)
    cbi = CSVBulkImport(handle=handle, has_title_line=has_title_line)
    rows = list(cbi.rows_as_dict(attr_names))
    assert rows == expected_result


def test_next_row_as_dict_throws_len_mismatch() -> None:
    """
    rows_as_dict should raise ValueError if attr_names isn't exactly the row
    length (2 in our sample).
    """
    handle = StringIO(CSV_NO_TITLE_LINE)
    cbi = CSVBulkImport(handle=handle, has_title_line=False)

    with pytest.raises(ValueError):
        next(cbi.rows_as_dict(["host_name"]))

    with pytest.raises(ValueError):
        next(cbi.rows_as_dict(["host_name", "ipaddress", "alias"]))
