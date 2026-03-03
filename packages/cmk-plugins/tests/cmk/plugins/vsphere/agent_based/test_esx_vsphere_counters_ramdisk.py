#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

from cmk.agent_based.v2 import Result, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters_ramdisk import (
    check_esx_vsphere_counters_ramdisk,
)

_MOCK_RESULT = [Result(state=State.OK, summary="mock filesystem result")]


def test_check_esx_vsphere_counters_ramdisk_all_negative_one() -> None:
    """Regression: ramdisk instance with all-(-1) samples must not appear in df list.

    When all counter samples are -1 (unavailable), that ramdisk entry is skipped
    and df_check_filesystem_list is called with an empty fslist → no results.
    """
    # Section with only "tmp", and its samples are all -1
    section = parse_esx_vsphere_counters(
        [
            [
                "sys.resourceMemConsumed",
                "host/system/kernel/kmanaged/visorfs/tmp",
                "-1#-1",
                "kiloBytes",
            ]
        ]
    )
    df_patch = (
        "cmk.plugins.vsphere.agent_based.esx_vsphere_counters_ramdisk.df_check_filesystem_list"
    )
    vs_patch = "cmk.plugins.vsphere.agent_based.esx_vsphere_counters_ramdisk.get_value_store"

    with (
        patch(df_patch, return_value=iter(_MOCK_RESULT)) as mock_df,
        patch(vs_patch, return_value={}),
    ):
        results = list(
            check_esx_vsphere_counters_ramdisk("tmp", FILESYSTEM_DEFAULT_PARAMS, section)
        )

    # df_check_filesystem_list is called with an empty fslist (tmp was skipped)
    assert mock_df.call_count == 1
    fslist_blocks = mock_df.call_args.kwargs["fslist_blocks"]
    assert fslist_blocks == []
    # and results come from df (which in real code returns nothing for empty fslist)
    # In this mock, it returns our mock result, but the key invariant is the empty fslist
    _ = results  # not the focus of this test; empty fslist is the assertion


def test_check_esx_vsphere_counters_ramdisk_valid_not_skipped() -> None:
    """Ramdisk instance with valid samples must be present in df list."""
    section = parse_esx_vsphere_counters(
        [
            [
                "sys.resourceMemConsumed",
                "host/system/kernel/kmanaged/visorfs/root",
                "16000#16000",
                "kiloBytes",
            ]
        ]
    )
    df_patch = (
        "cmk.plugins.vsphere.agent_based.esx_vsphere_counters_ramdisk.df_check_filesystem_list"
    )
    vs_patch = "cmk.plugins.vsphere.agent_based.esx_vsphere_counters_ramdisk.get_value_store"

    with (
        patch(df_patch, return_value=iter(_MOCK_RESULT)) as mock_df,
        patch(vs_patch, return_value={}),
    ):
        results = list(
            check_esx_vsphere_counters_ramdisk("root", FILESYSTEM_DEFAULT_PARAMS, section)
        )

    assert mock_df.call_count == 1
    fslist_blocks = mock_df.call_args.kwargs["fslist_blocks"]
    # root ramdisk (valid data) appears in fslist
    assert len(fslist_blocks) == 1
    assert fslist_blocks[0][0] == "root"
    assert results == _MOCK_RESULT
