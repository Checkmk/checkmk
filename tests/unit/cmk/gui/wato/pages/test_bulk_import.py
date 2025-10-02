# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from io import StringIO
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
    _prevent_reused_attr_names,
    ModeBulkImport,
)
from cmk.gui.watolib.csv_bulk_import import CSVBulkImport
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
    mode_bulk_import._has_title_line = has_title_line
    request.set_var("attribute_0", "host_name")
    request.set_var("attribute_1", "ipaddress")

    # Mock here is pretty unavoidable because of the use of nested function definitions
    with mock.patch("cmk.gui.wato.pages.bulk_import.ModeBulkImport._delete_csv_file"):
        mode_bulk_import._import(
            csv_bulk_import, host_attributes, debug=False, pprint_value=False, use_git=False
        )

    hosts = folder_tree().root_folder().hosts()
    assert len(hosts) == 3
    assert hosts[HostAddress("alinux01")].attributes["ipaddress"] == "10.10.10.1"
    assert hosts[HostAddress("alinux02")].attributes["ipaddress"] == "10.10.10.2"
    assert hosts[HostAddress("alinux03")].attributes["ipaddress"] == "10.10.10.3"


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
