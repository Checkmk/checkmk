#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ddn_s2a.agent_based.ddn_s2a_errors import (
    check_ddn_s2a_errors,
    discover_ddn_s2a_errors,
    parse_ddn_s2a_errors,
)

# Port 1 is a fibre channel port with one error of every kind, port 2 an
# infiniband one, which we don't monitor.
_RESPONSE = (
    "0@40@port_type@FC@link_failure_errs@1@lost_sync_errs@2@loss_of_sig_errs@3"
    "@prim_seq_errs@4@CRC_errs@5@receive_errs@6@CTIO_timeouts@7@CTIO_xmit_errs@8"
    "@CTIO_other_errs@9@port_type@IB@link_failure_errs@0@lost_sync_errs@0"
    "@loss_of_sig_errs@0@prim_seq_errs@0@CRC_errs@0@receive_errs@0@CTIO_timeouts@0"
    "@CTIO_xmit_errs@0@CTIO_other_errs@0@$"
)

_SECTION = parse_ddn_s2a_errors([[_RESPONSE]])


def test_discover_ddn_s2a_errors_skips_infiniband() -> None:
    # The levels are derived from the current counters, so that we get notified
    # about any new error.
    assert list(discover_ddn_s2a_errors(_SECTION)) == [
        Service(
            item="1",
            parameters={
                "link_failure_errs": (2, 6),
                "lost_sync_errs": (3, 7),
                "loss_of_signal_errs": (4, 8),
                "prim_seq_errs": (5, 9),
                "crc_errs": (6, 10),
                "receive_errs": (7, 11),
                "ctio_timeouts": (8, 12),
                "ctio_xmit_errs": (9, 13),
                "ctio_other_errs": (10, 14),
            },
        )
    ]


def test_check_ddn_s2a_errors() -> None:
    params = dict.fromkeys(_SECTION["1"].error_counts, (5, 8))

    assert list(check_ddn_s2a_errors("1", params, _SECTION)) == [
        Result(state=State.OK, summary="Link failure errors: 1"),
        Result(state=State.OK, summary="Lost sync errors: 2"),
        Result(state=State.OK, summary="Loss of signal errors: 3"),
        Result(state=State.OK, summary="PrimSeq errors: 4"),
        Result(state=State.WARN, summary="CRC errors: 5 (warn/crit at 5/8 errors)"),
        Result(state=State.WARN, summary="Receive errors: 6 (warn/crit at 5/8 errors)"),
        Result(state=State.WARN, summary="CTIO timeouts: 7 (warn/crit at 5/8 errors)"),
        Result(
            state=State.CRIT,
            summary="CTIO transmission errors: 8 (warn/crit at 5/8 errors)",
        ),
        Result(state=State.CRIT, summary="CTIO other errors: 9 (warn/crit at 5/8 errors)"),
    ]


def test_check_ddn_s2a_errors_vanished_port() -> None:
    assert not list(check_ddn_s2a_errors("3", {}, _SECTION))
