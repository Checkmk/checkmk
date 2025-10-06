# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from cmk.ccc.hostaddress import HostAddress
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.type_defs import Choices, CustomHostAttrSpec
from cmk.gui.wato.pages.bulk_import import (
    _attribute_choices,
    _detect_attribute,
    _host_rows_to_bulk,
    _prevent_reused_attr_names,
    CSVBulkImport,
    get_handle_for_csv,
    ImportTuple,
    ModeBulkImport,
)
from cmk.gui.watolib.host_attributes import all_host_attributes
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.utils.tags import TagGroup


def attr_choices_with_tag_groups_and_host_attrs(tag_groups: Sequence[TagGroup]) -> Choices:
    host_attrs = [
        CustomHostAttrSpec(
            add_custom_macro=False,
            help="What rack the machine is in",
            name="rack",
            show_in_table=False,
            title="Rack",
            topic="custom_attributes",
            type="TextAscii",
        ),
        CustomHostAttrSpec(
            add_custom_macro=False,
            help="What rack unit the machine is at",
            name="rack_u",
            show_in_table=False,
            title="Rack U",
            topic="custom_attributes",
            type="TextAscii",
        ),
    ]
    return _attribute_choices(tag_groups, host_attrs)


CSV_WITH_NON_ASCII_CHAR_IN_FIELD = """
thehostname,the_v4_ip_address
alinux01,10.10.10.1
alinux02-weird,1ö.1ö.1ö.2
alinux03,10.10.10.3
""".strip()

CSV_WITH_NON_ASCII_CHAR_IN_ALIAS = """
thehostname,the_v4_ip_address,alias
alinux01,10.10.10.1,Läufer01
alinux02-weird,10.10.10.2,Läufer02
alinux03,10.10.10.3,Läufer03
""".strip()

CSV_WITH_IP_VALIDATION_ERROR = """
thehostname,the_v4_ip_address
alinux01,10.10.10.1
alinux02-weird,ten...ten....ten....two
alinux03,10.10.10.3
""".strip()

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

EDGE_CASE_CSV_MALFORMED = """
host_name,ipaddress
server01;127.0.0.1
server02;127.0.0.2
"""


@pytest.mark.parametrize(
    "csvtext, has_title_line",
    [
        pytest.param(
            CSV_WITH_TITLE_LINE,
            True,
            id="normal csv with no blank lines and titles",
        ),
        pytest.param(
            CSV_NO_TITLE_LINE,
            False,
            id="normal csv with no blank lines and no titles",
        ),
        pytest.param(
            CSV_WITH_TITLE_LINE_BLANK_LINES_BEFORE,
            True,
            id="csv with title line and some blank lines before",
        ),
        pytest.param(
            EDGE_CASE_CSV_SCATTERED_NEWLINES_WITH_TITLE_LINE,
            True,
            id="csv with blank lines and titles",
        ),
        pytest.param(
            EDGE_CASE_CSV_SCATTERED_NEWLINES_NO_TITLE_LINE,
            False,
            id="csv with blank lines and no titles",
        ),
    ],
)
@pytest.mark.usefixtures(
    "request_context",
    "with_admin_login",
    "load_config",
    "suppress_bake_agents_in_background",
)
def test_bulk_import_csv_parsing(
    csvtext: str,
    has_title_line: bool,
) -> None:
    csv_bulk_import = CSVBulkImport(handle=StringIO(csvtext), has_title_line=has_title_line)
    host_attributes = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    )
    mode_bulk_import = ModeBulkImport()
    request.set_var("attribute_0", "host_name")
    request.set_var("attribute_1", "ipaddress")

    # Mock here is pretty unavoidable because of the use of nested function definitions
    with mock.patch("cmk.gui.wato.pages.bulk_import.ModeBulkImport._delete_csv_file"):
        mode_bulk_import._import(
            csv_bulk_import, host_attributes, debug=False, pprint_value=False, use_git=False
        )

    hosts = folder_tree().root_folder().hosts()
    assert len(hosts) == 3
    assert hosts[HostAddress("server01")].attributes["ipaddress"] == "192.168.1.101"
    assert hosts[HostAddress("server02")].attributes["ipaddress"] == "192.168.1.102"
    assert hosts[HostAddress("server03")].attributes["ipaddress"] == "192.168.1.103"


@pytest.mark.parametrize(
    "attributes",
    [
        ["hostname", "ipaddress", "hostname"],
        ["hostname", "ipaddress", "-", "-", "-", "ipaddress"],
    ],
)
def test_prevent_reused_attr_names_with_reuses(attributes: Sequence[str]) -> None:
    with pytest.raises(MKUserError):
        _prevent_reused_attr_names(attributes)


@pytest.mark.parametrize(
    "attributes",
    [
        ["hostname", "ipaddress"],
        ["hostname", "ipaddress", "-", "tag_agent"],
        ["hostname", "ipaddress", "-", "-", "-"],
    ],
)
def test_prevent_reused_attr_names_no_reuses(attributes: Sequence[str]) -> None:
    assert _prevent_reused_attr_names(attributes) is None  # type: ignore[func-returns-value]


@pytest.mark.usefixtures("request_context")
def test_attribute_choices() -> None:
    attr_choices_dict = dict(_attribute_choices([], []))
    assert "-" in attr_choices_dict
    assert None in attr_choices_dict
    assert "host_name" in attr_choices_dict
    assert "tag_agent" not in attr_choices_dict

    tag_groups = active_config.tags.tag_groups
    attr_choices_dict = dict(attr_choices_with_tag_groups_and_host_attrs(tag_groups))
    assert "-" in attr_choices_dict
    assert None in attr_choices_dict
    assert "host_name" in attr_choices_dict
    assert "tag_agent" in attr_choices_dict
    assert "rack" in attr_choices_dict
    assert "rack_u" in attr_choices_dict


@pytest.mark.parametrize(
    "header, expected",
    [
        ("host_name", "host_name"),
        ("host name", "host_name"),
        ("Host Name", "host_name"),
        ("IP Address", "ipaddress"),
        ("Nothing", ""),
        ("", ""),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_detect_attribute(
    header: str,
    expected: str,
) -> None:
    tag_groups = active_config.tags.tag_groups
    assert (
        _detect_attribute(attr_choices_with_tag_groups_and_host_attrs(tag_groups), header)
        == expected
    )


@pytest.mark.parametrize(
    "sample,headers,expected",
    [
        pytest.param(
            CSV_WITH_TITLE_LINE,
            ["host_name", "ipaddress"],
            [
                ("server01", {"ipaddress": "192.168.1.101"}, None),
                ("server02", {"ipaddress": "192.168.1.102"}, None),
                ("server03", {"ipaddress": "192.168.1.103"}, None),
            ],
            id="green path with two attributes",
        ),
        pytest.param(
            CSV_WITH_TITLE_LINE,
            ["host_name", "-"],
            [
                ("server01", {}, None),
                ("server02", {}, None),
                ("server03", {}, None),
            ],
            id="green path with one field unassigned",
        ),
        pytest.param(
            CSV_WITH_NON_ASCII_CHAR_IN_ALIAS,
            ["host_name", "ipaddress", "alias"],
            [
                ("alinux01", {"ipaddress": "10.10.10.1", "alias": "Läufer01"}, None),
                ("alinux02-weird", {"ipaddress": "10.10.10.2", "alias": "Läufer02"}, None),
                ("alinux03", {"ipaddress": "10.10.10.3", "alias": "Läufer03"}, None),
            ],
            id="alias may have non-ascii",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_host_rows_to_bulk(
    sample: str, headers: Sequence[str], expected: Sequence[ImportTuple]
) -> None:
    """
    Green path tests for _host_rows_to_bulk().
    """
    csv_bulk_import = CSVBulkImport(handle=StringIO(sample), has_title_line=True)
    raw_rows = csv_bulk_import.rows_as_dict(headers)
    host_attributes = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    )
    host_attribute_tuples = _host_rows_to_bulk(raw_rows, host_attributes)
    assert list(host_attribute_tuples) == expected


@pytest.mark.parametrize(
    "sample,headers,exc_matches",
    [
        pytest.param(
            CSV_WITH_NON_ASCII_CHAR_IN_FIELD,
            ["host_name", "ipaddress"],
            "Non-ASCII",
            id="non-ascii in field",
        ),
        pytest.param(
            CSV_WITH_IP_VALIDATION_ERROR,
            ["host_name", "ipaddress"],
            "Invalid host address",
            id="field does not pass validation",
        ),
        pytest.param(
            CSV_WITH_TITLE_LINE,
            ["-", "ipaddress"],
            "host name attribute",
            id="host_name not assigned",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_host_rows_to_bulk_exceptions(
    sample: str, headers: Sequence[str], exc_matches: str
) -> None:
    """
    Cases where _host_rows_to_bulk() is expected to raise an exception on bad input.
    """
    csv_bulk_import = CSVBulkImport(handle=StringIO(sample), has_title_line=True)
    raw_rows = csv_bulk_import.rows_as_dict(headers)
    host_attributes = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    )
    with pytest.raises(MKUserError, match=exc_matches):
        list(_host_rows_to_bulk(raw_rows, host_attributes))


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


def test_skip_to_and_return_next_row_throws_len_mismatch() -> None:
    """
    skip_to_and_return_next_row should report to the user if they have lines
    that aren't the same length as the first line (or header line) and bail out.
    """
    handle = StringIO(EDGE_CASE_CSV_MALFORMED)
    cbi = CSVBulkImport(handle=handle, has_title_line=True)

    with pytest.raises(MKUserError, match=r"^All rows"):
        cbi.skip_to_and_return_next_row()


def test_iter() -> None:
    handle = StringIO(CSV_WITH_TITLE_LINE)
    cbi = CSVBulkImport(handle=handle, has_title_line=True)
    assert list(cbi) == [
        ["server01", "192.168.1.101"],
        ["server02", "192.168.1.102"],
        ["server03", "192.168.1.103"],
    ]
