#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared helpers for filter table tests across editions.

Test cases exercising a filter class via the ``filter_registry`` lookup carry
their filter ``ident`` and the production filter is picked up from the registry.
Test cases exercising inventory filter classes (``FilterInvtable*`` /
``FilterInvText`` / ``FilterInvFloat``) construct the filter instance directly
with synthetic idents so the test does not depend on any production
inventory_ui plug-in being loaded.
"""

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.gui.inventory._tree import InventoryPath, TreeSource
from cmk.gui.inventory.filters import (
    FilterInvFloat,
    FilterInvFloatChoice,
    FilterInvtableAdminStatus,
    FilterInvtableAgeRange,
    FilterInvtableAvailable,
    FilterInvtableIntegerRange,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableText,
    FilterInvtableVersion,
    FilterInvText,
)
from cmk.gui.type_defs import Rows
from cmk.gui.visuals.filter import Filter
from cmk.inventory.structured_data import deserialize_tree, SDKey, SDNodeName


class FilterTableTest(NamedTuple):
    ident: str
    request_vars: Sequence[tuple[str, str]]
    rows: Rows
    expected_rows: Sequence[Mapping[str, Any]]
    # When set, the test should use this filter instance directly instead of
    # looking up ``ident`` in the global ``filter_registry``. Used for tests
    # of inventory filter classes that would otherwise require an
    # inventory_ui plug-in to register the filter at import time.
    filter: Filter | None = None


# --- Synthetic inventory filters used by the inv-* table test cases below.
# Each filter targets a test-only column name ("invtest_*") so the test rows
# are self-contained and do not coincide with any production inv_info ident.

_INV_BACKPLANE_DESC_FILTER = FilterInvtableText(
    inv_info="invtest",
    ident="invbackplane_description",
    title="Synthetic text filter",
)

_INV_VERSION_FILTER = FilterInvtableVersion(
    inv_info="invtest",
    ident="invtest_version",
    title="Synthetic version filter",
)

_INV_INDEX_FILTER = FilterInvtableIntegerRange(
    inv_info="invtest",
    ident="invtest_index",
    title="Synthetic integer-range filter",
    unit_choices={},
)

# FilterInvtableOperStatus / AdminStatus / Available hard-code the column name
# they read from the row (`invinterface_oper_status` / `_admin_status` /
# `_available`) — see cmk/gui/query_filters.py:if_oper_status_filter_table and
# the inline lambdas in cmk/gui/inventory/filters.py:797-836. Test rows must
# use those names; the filter is still constructed locally here (not via the
# plug-in registry).
_INV_OPER_STATUS_FILTER = FilterInvtableOperStatus(
    inv_info="invtest",
    ident="invinterface_oper_status",
    title="Synthetic operational-status filter",
)

_INV_ADMIN_STATUS_FILTER = FilterInvtableAdminStatus(
    inv_info="invtest",
    ident="invinterface_admin_status",
    title="Synthetic administrative-status filter",
)

_INV_AVAILABLE_FILTER = FilterInvtableAvailable(
    inv_info="invtest",
    ident="invinterface_available",
    title="Synthetic available filter",
)

_INV_PORT_TYPE_FILTER = FilterInvtableInterfaceType(
    inv_info="invtest",
    ident="invtest_port_type",
    title="Synthetic interface-type filter",
)

# FilterInvtableAgeRange has the request-var shape used by the test data
# (`_from`/`_from_prefix`/`_until`/`_until_prefix`). The sibling
# FilterInvtableTimestampAsAge uses a different `_days`-suffixed shape; the
# original test (when registered via inventory_ui) was the AgeRange variant.
_INV_LAST_CHANGE_FILTER = FilterInvtableAgeRange(
    inv_info="invtest",
    ident="invtest_last_change",
    title="Synthetic age-range filter",
    unit_choices={
        "": FilterInvFloatChoice("s", 1),
        "min": FilterInvFloatChoice("min", 60),
        "h": FilterInvFloatChoice("h", 3600),
        "d": FilterInvFloatChoice("d", 86400),
    },
)

# Inv-attribute filters used by the filter_inv_table_tests block.
_INV_OS_VENDOR_FILTER = FilterInvText(
    ident="inv_test_os_vendor",
    title="Synthetic inv-text filter",
    inventory_path=InventoryPath(
        path=(SDNodeName("software"), SDNodeName("os")),
        source=TreeSource.attributes,
        key=SDKey("vendor"),
    ),
)

_INV_BUS_SPEED_FILTER = FilterInvFloat(
    ident="inv_test_bus_speed",
    title="Synthetic inv-float filter",
    inventory_path=InventoryPath(
        path=(SDNodeName("hardware"), SDNodeName("cpu")),
        source=TreeSource.attributes,
        key=SDKey("bus_speed"),
    ),
    unit_choices={"M": FilterInvFloatChoice("MHz", 1000000)},
)


filter_table_tests = [
    # Testing base class BIStatusFilter
    FilterTableTest(
        ident="aggr_assumed_state",
        request_vars=[("bias0", "on"), ("bias1", "on"), ("bias_filled", "1")],
        rows=[
            {"aggr_assumed_state": {"state": 0}},
            {"aggr_assumed_state": {"state": 1}},
            {"aggr_assumed_state": {"state": 2}},
        ],
        expected_rows=[
            {"aggr_assumed_state": {"state": 0}},
            {"aggr_assumed_state": {"state": 1}},
        ],
    ),
    # Testing base class Filter
    FilterTableTest(
        ident="aggr_group",
        request_vars=[("aggr_group", "blä")],
        rows=[
            {"aggr_group": "blub"},
            {"aggr_group": "blä"},
        ],
        expected_rows=[
            {"aggr_group": "blä"},
        ],
    ),
    FilterTableTest(
        ident="aggr_hosts",
        request_vars=[
            ("aggr_host_host", "z"),
        ],
        rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "a"), ("s", "c")]},
            {"aggr_hosts": [("s", "a"), ("s", "g")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
        expected_rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
    ),
    FilterTableTest(
        ident="aggr_hosts",
        request_vars=[
            ("aggr_host_site", ""),
            ("aggr_host_host", "z"),
        ],
        rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "a"), ("s", "c")]},
            {"aggr_hosts": [("s", "a"), ("s", "g")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
        expected_rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
    ),
    FilterTableTest(
        ident="aggr_hosts",
        request_vars=[
            ("aggr_host_site", "d"),
            ("aggr_host_host", "z"),
        ],
        rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "a"), ("s", "c")]},
            {"aggr_hosts": [("s", "a"), ("s", "g")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
        expected_rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
    ),
    # Testing base class BITextFilter
    FilterTableTest(
        ident="aggr_name",
        request_vars=[("aggr_name", "a")],
        rows=[
            {"aggr_name": "a"},
            {"aggr_name": "aaa"},
            {"aggr_name": "b"},
            {"aggr_name": "c"},
        ],
        expected_rows=[
            {"aggr_name": "a"},
        ],
    ),
    # Testing base class FilterTriState
    FilterTableTest(
        ident="aggr_service_used",
        request_vars=[("is_aggr_service_used", "0")],
        rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
        ],
        expected_rows=[
            {"host_name": "h", "service_description": "srv2", "site": "s"},
            {"host_name": "h2", "service_description": "srv2", "site": "s"},
        ],
    ),
    FilterTableTest(
        ident="aggr_service_used",
        request_vars=[("is_aggr_service_used", "1")],
        rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
        ],
        expected_rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
        ],
    ),
    FilterTableTest(
        ident="aggr_service_used",
        request_vars=[("is_aggr_service_used", "-1")],
        rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
            {"site": "b", "host_name": "h", "service_description": "srv1"},
        ],
        expected_rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
            {"site": "b", "host_name": "h", "service_description": "srv1"},
        ],
    ),
    # Testing base class DeploymentTristateFilter
    FilterTableTest(
        ident="deployment_has_agent",
        request_vars=[("is_deployment_has_agent", "0")],
        rows=[
            {"host_name": "abc"},
            {"host_name": "zzz"},
        ],
        expected_rows=[
            {"host_name": "zzz"},
        ],
    ),
    FilterTableTest(
        ident="deployment_has_agent",
        request_vars=[("is_deployment_has_agent", "1")],
        rows=[],
        expected_rows=[],
    ),
    FilterTableTest(
        ident="deployment_has_agent",
        request_vars=[("is_deployment_has_agent", "-1")],
        rows=[
            {"host_name": "abc"},
            {"host_name": "zzz"},
        ],
        expected_rows=[
            {"host_name": "abc"},
            {"host_name": "zzz"},
        ],
    ),
    FilterTableTest(
        ident="discovery_state",
        request_vars=[
            ("discovery_state_ignored", "on"),
            ("discovery_state_vanished", "on"),
            ("discovery_state_unmonitored", ""),
        ],
        rows=[
            {"discovery_state": "ignored"},
            {"discovery_state": "vanished"},
            {"discovery_state": "unmonitored"},
        ],
        expected_rows=[
            {"discovery_state": "ignored"},
            {"discovery_state": "vanished"},
        ],
    ),
    # Testing base class FilterInvtableText (synthetic filter)
    FilterTableTest(
        ident=_INV_BACKPLANE_DESC_FILTER.ident,
        filter=_INV_BACKPLANE_DESC_FILTER,
        request_vars=[
            ("invbackplane_description", "lulu"),
        ],
        rows=[
            {"invbackplane_description": "lulu"},
            {"invbackplane_description": "lele"},
        ],
        expected_rows=[
            {"invbackplane_description": "lulu"},
        ],
    ),
    # Testing base class FilterInvtableVersion (synthetic filter)
    FilterTableTest(
        ident=_INV_VERSION_FILTER.ident,
        filter=_INV_VERSION_FILTER,
        request_vars=[],
        rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
        expected_rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
    ),
    FilterTableTest(
        ident=_INV_VERSION_FILTER.ident,
        filter=_INV_VERSION_FILTER,
        request_vars=[
            ("invtest_version_from", "1.0"),
        ],
        rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
        expected_rows=[
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
    ),
    FilterTableTest(
        ident=_INV_VERSION_FILTER.ident,
        filter=_INV_VERSION_FILTER,
        request_vars=[
            ("invtest_version_until", "3.0"),
        ],
        rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
        expected_rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
        ],
    ),
    FilterTableTest(
        ident=_INV_VERSION_FILTER.ident,
        filter=_INV_VERSION_FILTER,
        request_vars=[
            ("invtest_version_from", "1.0"),
            ("invtest_version_until", "3.0"),
        ],
        rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
        expected_rows=[
            {"invtest_version": "1.5.1"},
            {"invtest_version": "2.0.0"},
        ],
    ),
    FilterTableTest(
        ident=_INV_VERSION_FILTER.ident,
        filter=_INV_VERSION_FILTER,
        request_vars=[],
        rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": None},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
        expected_rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": None},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
    ),
    FilterTableTest(
        ident=_INV_VERSION_FILTER.ident,
        filter=_INV_VERSION_FILTER,
        request_vars=[
            ("invtest_version_from", "1.0"),
            ("invtest_version_until", "3.0"),
        ],
        rows=[
            {"invtest_version": "0.5"},
            {"invtest_version": "0.5.1"},
            {"invtest_version": None},
            {"invtest_version": "2.0.0"},
            {"invtest_version": "4.5.1"},
        ],
        expected_rows=[
            {"invtest_version": "2.0.0"},
        ],
    ),
    # Testing base class FilterInvtableIntegerRange (synthetic filter)
    FilterTableTest(
        ident=_INV_INDEX_FILTER.ident,
        filter=_INV_INDEX_FILTER,
        request_vars=[
            ("invtest_index_from", "3"),
            ("invtest_index_until", "10"),
        ],
        rows=[
            {"invtest_index": 1},
            {"invtest_index": 3},
            {"invtest_index": 5},
            {"invtest_index": 11},
        ],
        expected_rows=[
            {"invtest_index": 3},
            {"invtest_index": 5},
        ],
    ),
    # Testing base class FilterInvtableOperStatus (synthetic filter)
    FilterTableTest(
        ident=_INV_OPER_STATUS_FILTER.ident,
        filter=_INV_OPER_STATUS_FILTER,
        request_vars=[],
        rows=[
            {"invinterface_oper_status": 1},
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
        expected_rows=[
            {"invinterface_oper_status": 1},
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
    ),
    FilterTableTest(
        ident=_INV_OPER_STATUS_FILTER.ident,
        filter=_INV_OPER_STATUS_FILTER,
        request_vars=[
            ("invinterface_oper_status_1", ""),
            ("invinterface_oper_status_3", "on"),
            ("invinterface_oper_status_5", ""),
        ],
        rows=[
            {"invinterface_oper_status": 1},
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
        expected_rows=[
            {"invinterface_oper_status": 3},
        ],
    ),
    FilterTableTest(
        ident=_INV_OPER_STATUS_FILTER.ident,
        filter=_INV_OPER_STATUS_FILTER,
        request_vars=[
            ("invinterface_oper_status_1", ""),
            ("invinterface_oper_status_3", ""),
            ("invinterface_oper_status_5", ""),
        ],
        rows=[
            {"invinterface_oper_status": 1},
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
        expected_rows=[],
    ),
    FilterTableTest(
        ident=_INV_OPER_STATUS_FILTER.ident,
        filter=_INV_OPER_STATUS_FILTER,
        request_vars=[
            ("invinterface_oper_status_1", ""),
            ("invinterface_oper_status_3", "on"),
        ],
        rows=[
            {"invinterface_oper_status": 1},
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
        expected_rows=[
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
    ),
    # Testing base class FilterInvtableAdminStatus (synthetic filter).
    # Backed by SingleOptionQuery: the single request var carries the chosen
    # status ("1" up, "2" down, "-1" ignore).
    FilterTableTest(
        ident=_INV_ADMIN_STATUS_FILTER.ident,
        filter=_INV_ADMIN_STATUS_FILTER,
        request_vars=[
            (_INV_ADMIN_STATUS_FILTER.ident, "1"),
        ],
        rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
        expected_rows=[
            {"invinterface_admin_status": "1"},
        ],
    ),
    FilterTableTest(
        ident=_INV_ADMIN_STATUS_FILTER.ident,
        filter=_INV_ADMIN_STATUS_FILTER,
        request_vars=[
            (_INV_ADMIN_STATUS_FILTER.ident, "2"),
        ],
        rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
        expected_rows=[
            {"invinterface_admin_status": "2"},
        ],
    ),
    FilterTableTest(
        ident=_INV_ADMIN_STATUS_FILTER.ident,
        filter=_INV_ADMIN_STATUS_FILTER,
        request_vars=[
            (_INV_ADMIN_STATUS_FILTER.ident, "-1"),
        ],
        rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
        expected_rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
    ),
    # Testing base class FilterInvtableAvailable (synthetic filter).
    # Backed by SingleOptionQuery: "no" → keep used (False), "yes" → keep
    # free (True), "" → ignore.
    FilterTableTest(
        ident=_INV_AVAILABLE_FILTER.ident,
        filter=_INV_AVAILABLE_FILTER,
        request_vars=[
            (_INV_AVAILABLE_FILTER.ident, "no"),
        ],
        rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
        expected_rows=[
            {"invinterface_available": False},
        ],
    ),
    FilterTableTest(
        ident=_INV_AVAILABLE_FILTER.ident,
        filter=_INV_AVAILABLE_FILTER,
        request_vars=[
            (_INV_AVAILABLE_FILTER.ident, "yes"),
        ],
        rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
        expected_rows=[
            {"invinterface_available": True},
        ],
    ),
    FilterTableTest(
        ident=_INV_AVAILABLE_FILTER.ident,
        filter=_INV_AVAILABLE_FILTER,
        request_vars=[],
        rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
        expected_rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
    ),
    # Testing base class FilterInvtableInterfaceType (synthetic filter)
    FilterTableTest(
        ident=_INV_PORT_TYPE_FILTER.ident,
        filter=_INV_PORT_TYPE_FILTER,
        request_vars=[
            ("invtest_port_type", "2|3|10"),
        ],
        rows=[
            {"invtest_port_type": "1"},
            {"invtest_port_type": "2"},
            {"invtest_port_type": "10"},
        ],
        expected_rows=[
            {"invtest_port_type": "2"},
            {"invtest_port_type": "10"},
        ],
    ),
    # Testing base class FilterInvtableTimestampAsAge (synthetic filter)
    FilterTableTest(
        ident=_INV_LAST_CHANGE_FILTER.ident,
        filter=_INV_LAST_CHANGE_FILTER,
        request_vars=[
            ("invtest_last_change_from", "1"),
            ("invtest_last_change_from_prefix", "d"),
            ("invtest_last_change_until", "5"),
            ("invtest_last_change_until_prefix", "d"),
        ],
        rows=[
            {"invtest_last_change": 1523811000},
            {"invtest_last_change": 1523811000 - (60 * 60 * 24 * 10)},
            {"invtest_last_change": 1523811000 - (60 * 60 * 24 * 4)},
        ],
        expected_rows=[
            {"invtest_last_change": 1523811000 - (60 * 60 * 24 * 4)},
        ],
    ),
    # FilterECServiceLevelRange
    FilterTableTest(
        ident="svc_service_level",
        request_vars=[("svc_service_level_lower", "1"), ("svc_service_level_upper", "3")],
        rows=[
            {
                "service_custom_variables": {"EC_SL": "0"},
            },
            {
                "service_custom_variables": {"EC_SL": "1"},
            },
            {
                "service_custom_variables": {"EC_SL": "2"},
            },
            {
                "service_custom_variables": {"EC_SL": "3"},
            },
            {
                "service_custom_variables": {"EC_SL": "4"},
            },
        ],
        expected_rows=[
            {
                "service_custom_variables": {"EC_SL": "1"},
            },
            {
                "service_custom_variables": {"EC_SL": "2"},
            },
            {
                "service_custom_variables": {"EC_SL": "3"},
            },
        ],
    ),
    FilterTableTest(
        ident="hst_service_level",
        request_vars=[("hst_service_level_lower", "1")],
        rows=[
            {
                "host_custom_variables": {"EC_SL": "0"},
            },
            {
                "host_custom_variables": {"EC_SL": "1"},
            },
            {
                "host_custom_variables": {"EC_SL": "2"},
            },
        ],
        expected_rows=[
            {
                "host_custom_variables": {"EC_SL": "1"},
            },
        ],
    ),
    FilterTableTest(
        ident="hst_service_level",
        request_vars=[("hst_service_level_upper", "2")],
        rows=[
            {
                "host_custom_variables": {"EC_SL": "0"},
            },
            {
                "host_custom_variables": {"EC_SL": "1"},
            },
            {
                "host_custom_variables": {"EC_SL": "2"},
            },
        ],
        expected_rows=[
            {
                "host_custom_variables": {"EC_SL": "2"},
            },
        ],
    ),
    # TODO: Testing base class FilterHistoric
    # FilterTableTest(
    #    ident="host_metrics_hist",
    #    request_vars=[
    #        ('cutoff', "10"),
    #    ],
    #    rows=[
    #    ],
    #    expected_rows=[
    #    ],
    # ),
]


filter_inv_table_tests = [
    # Filter out filled trees (is_has_inv == 0)
    FilterTableTest(
        ident="has_inv",
        request_vars=[
            ("is_has_inv", "0"),
        ],
        rows=[
            {"host_inventory": deserialize_tree({})},
            {"host_inventory": deserialize_tree({"a": "b"})},
        ],
        expected_rows=[
            {"host_inventory": deserialize_tree({})},
        ],
    ),
    # Filter out empty trees (is_has_inv == 1)
    FilterTableTest(
        ident="has_inv",
        request_vars=[
            ("is_has_inv", "1"),
        ],
        rows=[
            {"host_inventory": deserialize_tree({})},
            {"host_inventory": deserialize_tree({"a": "b"})},
        ],
        expected_rows=[
            {"host_inventory": deserialize_tree({"a": "b"})},
        ],
    ),
    # Do not apply filter (is_has_inv == -1)
    FilterTableTest(
        ident="has_inv",
        request_vars=[
            ("is_has_inv", "-1"),
        ],
        rows=[
            {"host_inventory": deserialize_tree({})},
            {"host_inventory": deserialize_tree({"a": "b"})},
        ],
        expected_rows=[
            {"host_inventory": deserialize_tree({})},
            {"host_inventory": deserialize_tree({"a": "b"})},
        ],
    ),
    # Testing base class FilterInvText (synthetic filter)
    FilterTableTest(
        ident=_INV_OS_VENDOR_FILTER.ident,
        filter=_INV_OS_VENDOR_FILTER,
        request_vars=[
            (_INV_OS_VENDOR_FILTER.ident, "bla"),
        ],
        rows=[
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "bla"}}})},
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "blabla"}}})},
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "ag blabla"}}})},
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "blu"}}})},
        ],
        expected_rows=[
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "bla"}}})},
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "blabla"}}})},
            {"host_inventory": deserialize_tree({"software": {"os": {"vendor": "ag blabla"}}})},
        ],
    ),
    # Testing base class FilterInvFloat (synthetic filter)
    FilterTableTest(
        ident=_INV_BUS_SPEED_FILTER.ident,
        filter=_INV_BUS_SPEED_FILTER,
        request_vars=[
            ("inv_test_bus_speed_from", "10"),
            ("inv_test_bus_speed_from_prefix", "M"),
            ("inv_test_bus_speed_until", "20"),
            ("inv_test_bus_speed_until_prefix", "M"),
        ],
        rows=[
            {"host_inventory": deserialize_tree({"hardware": {"cpu": {"bus_speed": 1000000}}})},
            {"host_inventory": deserialize_tree({"hardware": {"cpu": {"bus_speed": 15000000}}})},
            {"host_inventory": deserialize_tree({"hardware": {"cpu": {"bus_speed": 21000000}}})},
        ],
        expected_rows=[
            {"host_inventory": deserialize_tree({"hardware": {"cpu": {"bus_speed": 15000000}}})},
        ],
    ),
]
