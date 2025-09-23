# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import csv
from unittest import mock

import pytest

from cmk.utils.hostaddress import HostAddress
from cmk.gui.http import request
from cmk.gui.wato.pages.bulk_import import ModeBulkImport
from cmk.gui.watolib.hosts_and_folders import folder_tree

CSV_NORMAL_WITH_TITLE = """
thehostname,the_v4_ip_address
alinux01,10.10.10.1
alinux02,10.10.10.2
alinux03,10.10.10.3
""".strip()

CSV_NORMAL_NO_TITLE = """
alinux01,10.10.10.1
alinux02,10.10.10.2
alinux03,10.10.10.3
""".strip()

CSV_WITH_NEWLINES_AND_TITLE = """

thehostname,the_v4_ip_address

alinux01,10.10.10.1

alinux02,10.10.10.2

alinux03,10.10.10.3

"""

CSV_WITH_NEWLINES_NO_TITLE = """


alinux01,10.10.10.1


alinux02,10.10.10.2

alinux03,10.10.10.3

"""


@pytest.mark.parametrize(
    "csvtext, has_title_line",
    [
        pytest.param(
            CSV_NORMAL_WITH_TITLE,
            True,
            id="normal csv with no blank lines and titles",
        ),
        pytest.param(
            CSV_NORMAL_NO_TITLE,
            False,
            id="normal csv with no blank lines and no titles",
        ),
        pytest.param(
            CSV_WITH_NEWLINES_AND_TITLE,
            True,
            id="csv with blank lines and titles",
        ),
        pytest.param(
            CSV_WITH_NEWLINES_NO_TITLE,
            False,
            id="csv with blank lines and no titles",
        ),
    ],
)
@pytest.mark.usefixtures(
    "request_context",
    "with_admin_login",
    "suppress_bake_agents_in_background",
)
def test_bulk_import_csv_parsing(
    csvtext: str,
    has_title_line: bool,
) -> None:
    csv_dialect = csv.Sniffer().sniff(csvtext, delimiters=",;\t:")
    csv_reader = csv.reader(csvtext.split("\n"), csv_dialect)
    mode_bulk_import = ModeBulkImport()
    mode_bulk_import._has_title_line = has_title_line
    request.set_var("attribute_0", "host_name")
    request.set_var("attribute_1", "ipaddress")

    # Mock here is pretty unavoidable because of the use of nested function definitions
    with mock.patch("cmk.gui.wato.pages.bulk_import.ModeBulkImport._delete_csv_file"):
        mode_bulk_import._import(csv_reader)

    hosts = folder_tree().root_folder().hosts()
    assert len(hosts) == 3
    assert hosts[HostAddress("alinux01")].attributes["ipaddress"] == "10.10.10.1"
    assert hosts[HostAddress("alinux02")].attributes["ipaddress"] == "10.10.10.2"
    assert hosts[HostAddress("alinux03")].attributes["ipaddress"] == "10.10.10.3"
