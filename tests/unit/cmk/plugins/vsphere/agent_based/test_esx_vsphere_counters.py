#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib import interfaces
from cmk.plugins.vsphere.agent_based import esx_vsphere_counters


def test_parse_esx_vsphere_counters() -> None:
    assert esx_vsphere_counters.parse_esx_vsphere_counters(
        [
            ["disk.numberReadAveraged", "naa.5000cca05688e814", "0#0", "number"],
            ["disk.numberReadAveraged", "naa.60002ac0000000000000000e0000586d", "0#0", "number"],
            ["disk.write", "naa.6000eb39f31c58130000000000000015", "0#0", "kiloBytesPerSecond"],
            ["net.bytesRx", "vmnic0", "1#1", "kiloBytesPerSecond"],
            ["net.droppedRx", "vmnic1", "0#0", "number"],
            ["net.errorsRx", "", "0#0", "number"],
            ["net.errorsRx", "vmnic2", "0#0", "number"],
            ["net.errorsTx", "", "0#0", "number"],
            ["net.packetsTx", "", "3162#3488", "number"],
            ["net.received", "vmnic0", "1#1", "kiloBytesPerSecond"],
            ["net.received", "vmnic5", "63#46", "kiloBytesPerSecond"],
            ["net.transmitted", "vmnic3", "0#0", "kiloBytesPerSecond"],
            ["sys.resourceMemConsumed", "host/user", "83527720#83529784", "kiloBytes"],
            ["sys.resourceMemConsumed", "host/vim/vmvisor", "291820#291832", "kiloBytes"],
            ["sys.resourceMemConsumed", "host/vim/vmvisor/init", "1568#1568", "kiloBytes"],
            ["sys.resourceMemConsumed", "host/vim/vmvisor/ntpd", "1572#1572", "kiloBytes"],
            ["sys.resourceMemConsumed", "host/vim/vmvisor/vmkdevmgr", "5304#5304", "kiloBytes"],
            ["sys.resourceMemConsumed", "host/vim/vmvisor/vmsupport", "0#0", "kiloBytes"],
            ["sys.resourceMemConsumed", "host/vim/vmvisor/vvold", "9192#9192", "kiloBytes"],
            ["net.macaddress", "vmnic4", "64:51:06:f0:c5:d0", "mac"],
            ["gpu.mem.reserved", "gpu1", "2219712#2219712", "kiloBytes"],
            ["gpu.mem.total", "gpu1", "23580672#23580672", "kiloBytes"],
            ["gpu.mem.usage", "gpu1", "941#941", "percent"],
            ["gpu.mem.used", "gpu1", "2219712#2219712", "kiloBytes"],
            ["gpu.power.used", "gpu1", "24#24", "watt"],
            ["gpu.temperature", "gpu1", "37#37", "celsius"],
            ["gpu.utilization", "gpu1", "42#42", "percent"],
        ]
    ) == {
        "disk.numberReadAveraged": {
            "naa.5000cca05688e814": [(["0", "0"], "number")],
            "naa.60002ac0000000000000000e0000586d": [(["0", "0"], "number")],
        },
        "disk.write": {
            "naa.6000eb39f31c58130000000000000015": [(["0", "0"], "kiloBytesPerSecond")]
        },
        "net.bytesRx": {"vmnic0": [(["1", "1"], "kiloBytesPerSecond")]},
        "net.droppedRx": {"vmnic1": [(["0", "0"], "number")]},
        "net.errorsRx": {"": [(["0", "0"], "number")], "vmnic2": [(["0", "0"], "number")]},
        "net.errorsTx": {"": [(["0", "0"], "number")]},
        "net.macaddress": {"vmnic4": [(["64:51:06:f0:c5:d0"], "mac")]},
        "net.packetsTx": {"": [(["3162", "3488"], "number")]},
        "net.received": {
            "vmnic0": [(["1", "1"], "kiloBytesPerSecond")],
            "vmnic5": [(["63", "46"], "kiloBytesPerSecond")],
        },
        "net.transmitted": {"vmnic3": [(["0", "0"], "kiloBytesPerSecond")]},
        "sys.resourceMemConsumed": {
            "host/user": [(["83527720", "83529784"], "kiloBytes")],
            "host/vim/vmvisor": [(["291820", "291832"], "kiloBytes")],
            "host/vim/vmvisor/init": [(["1568", "1568"], "kiloBytes")],
            "host/vim/vmvisor/ntpd": [(["1572", "1572"], "kiloBytes")],
            "host/vim/vmvisor/vmkdevmgr": [(["5304", "5304"], "kiloBytes")],
            "host/vim/vmvisor/vmsupport": [(["0", "0"], "kiloBytes")],
            "host/vim/vmvisor/vvold": [(["9192", "9192"], "kiloBytes")],
        },
        "gpu.mem.reserved": {"gpu1": [(["2219712", "2219712"], "kiloBytes")]},
        "gpu.mem.total": {"gpu1": [(["23580672", "23580672"], "kiloBytes")]},
        "gpu.mem.usage": {"gpu1": [(["941", "941"], "percent")]},
        "gpu.mem.used": {"gpu1": [(["2219712", "2219712"], "kiloBytes")]},
        "gpu.power.used": {"gpu1": [(["24", "24"], "watt")]},
        "gpu.temperature": {"gpu1": [(["37", "37"], "celsius")]},
        "gpu.utilization": {"gpu1": [(["42", "42"], "percent")]},
    }


def test_convert_esx_counters_if() -> None:
    assert esx_vsphere_counters.convert_esx_counters_if(
        OrderedDict(
            {
                "net.bandwidth": {
                    "vmnic0": [(["1000000000"], "bytes")],
                    "vmnic4": [(["10000000000"], "bytes")],
                    "vmnic5": [(["10000000000"], "bytes")],
                },
                "net.broadcastRx": {
                    "": [(["660", "592"], "number")],
                    "vmnic0": [(["220", "200"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["220", "196"], "number")],
                    "vmnic5": [(["220", "196"], "number")],
                },
                "net.broadcastTx": {
                    "": [(["0", "4"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "4"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.bytesRx": {
                    "": [(["84", "234"], "kiloBytesPerSecond")],
                    "vmnic0": [(["1", "1"], "kiloBytesPerSecond")],
                    "vmnic1": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic2": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic3": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic4": [(["19", "187"], "kiloBytesPerSecond")],
                    "vmnic5": [(["63", "46"], "kiloBytesPerSecond")],
                },
                "net.bytesTx": {
                    "": [(["962", "675"], "kiloBytesPerSecond")],
                    "vmnic0": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic1": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic2": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic3": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic4": [(["33", "118"], "kiloBytesPerSecond")],
                    "vmnic5": [(["928", "557"], "kiloBytesPerSecond")],
                },
                "net.droppedRx": {
                    "": [(["0", "0"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "0"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.droppedTx": {
                    "": [(["0", "0"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "0"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.errorsRx": {
                    "": [(["0", "0"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "0"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.errorsTx": {
                    "": [(["0", "0"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "0"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.macaddress": {
                    "vmnic0": [(["1c:c1:de:1b:ec:dc"], "mac")],
                    "vmnic1": [(["1c:c1:de:1b:ec:de"], "mac")],
                    "vmnic2": [(["1c:c1:de:1b:ec:e0"], "mac")],
                    "vmnic3": [(["1c:c1:de:1b:ec:e2"], "mac")],
                    "vmnic4": [(["64:51:06:f0:c5:d0"], "mac")],
                    "vmnic5": [(["64:51:06:f0:c5:d4"], "mac")],
                },
                "net.multicastRx": {
                    "": [(["470", "212"], "number")],
                    "vmnic0": [(["157", "71"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["157", "70"], "number")],
                    "vmnic5": [(["156", "71"], "number")],
                },
                "net.multicastTx": {
                    "": [(["0", "0"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "0"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.packetsRx": {
                    "": [(["7417", "7204"], "number")],
                    "vmnic0": [(["383", "266"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["952", "3922"], "number")],
                    "vmnic5": [(["6082", "3016"], "number")],
                },
                "net.packetsTx": {
                    "": [(["3162", "3488"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["401", "1892"], "number")],
                    "vmnic5": [(["2761", "1596"], "number")],
                },
                "net.received": {
                    "": [(["84", "234"], "kiloBytesPerSecond")],
                    "vmnic0": [(["1", "1"], "kiloBytesPerSecond")],
                    "vmnic1": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic2": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic3": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic4": [(["19", "187"], "kiloBytesPerSecond")],
                    "vmnic5": [(["63", "46"], "kiloBytesPerSecond")],
                },
                "net.state": {
                    "vmnic0": [(["1"], "state")],
                    "vmnic1": [(["2"], "state")],
                    "vmnic2": [(["2"], "state")],
                    "vmnic3": [(["2"], "state")],
                    "vmnic4": [(["1"], "state")],
                    "vmnic5": [(["1"], "state")],
                },
                "net.transmitted": {
                    "": [(["962", "675"], "kiloBytesPerSecond")],
                    "vmnic0": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic1": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic2": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic3": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic4": [(["33", "118"], "kiloBytesPerSecond")],
                    "vmnic5": [(["928", "557"], "kiloBytesPerSecond")],
                },
                "net.unknownProtos": {
                    "": [(["0", "0"], "number")],
                    "vmnic0": [(["0", "0"], "number")],
                    "vmnic1": [(["0", "0"], "number")],
                    "vmnic2": [(["0", "0"], "number")],
                    "vmnic3": [(["0", "0"], "number")],
                    "vmnic4": [(["0", "0"], "number")],
                    "vmnic5": [(["0", "0"], "number")],
                },
                "net.usage": {
                    "": [(["1046", "910"], "kiloBytesPerSecond")],
                    "vmnic0": [(["1", "1"], "kiloBytesPerSecond")],
                    "vmnic1": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic2": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic3": [(["0", "0"], "kiloBytesPerSecond")],
                    "vmnic4": [(["53", "305"], "kiloBytesPerSecond")],
                    "vmnic5": [(["991", "603"], "kiloBytesPerSecond")],
                },
            }
        )
    ) == [
        interfaces.InterfaceWithRates(
            interfaces.Attributes(
                index="1",
                descr="vmnic0",
                alias="vmnic0",
                type="6",
                speed=1000000000,
                oper_status="1",
                phys_address="\x1cÁÞ\x1bìÜ",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Rates(
                in_octets=1024,
                in_ucast=324,
                in_mcast=114,
                in_bcast=210,
                in_disc=0,
                in_err=0,
                out_octets=0,
                out_ucast=0,
                out_mcast=0,
                out_bcast=0,
                out_disc=0,
                out_err=0,
            ),
            get_rate_errors=[],
        ),
        interfaces.InterfaceWithRates(
            interfaces.Attributes(
                index="2",
                descr="vmnic1",
                alias="vmnic1",
                type="6",
                speed=0,
                oper_status="2",
                phys_address="\x1cÁÞ\x1bìÞ",
                oper_status_name="down",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Rates(
                in_octets=0,
                in_ucast=0,
                in_mcast=0,
                in_bcast=0,
                in_disc=0,
                in_err=0,
                out_octets=0,
                out_ucast=0,
                out_mcast=0,
                out_bcast=0,
                out_disc=0,
                out_err=0,
            ),
            get_rate_errors=[],
        ),
        interfaces.InterfaceWithRates(
            interfaces.Attributes(
                index="3",
                descr="vmnic2",
                alias="vmnic2",
                type="6",
                speed=0,
                oper_status="2",
                phys_address="\x1cÁÞ\x1bìà",
                oper_status_name="down",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Rates(
                in_octets=0,
                in_ucast=0,
                in_mcast=0,
                in_bcast=0,
                in_disc=0,
                in_err=0,
                out_octets=0,
                out_ucast=0,
                out_mcast=0,
                out_bcast=0,
                out_disc=0,
                out_err=0,
            ),
            get_rate_errors=[],
        ),
        interfaces.InterfaceWithRates(
            interfaces.Attributes(
                index="4",
                descr="vmnic3",
                alias="vmnic3",
                type="6",
                speed=0,
                oper_status="2",
                phys_address="\x1cÁÞ\x1bìâ",
                oper_status_name="down",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Rates(
                in_octets=0,
                in_ucast=0,
                in_mcast=0,
                in_bcast=0,
                in_disc=0,
                in_err=0,
                out_octets=0,
                out_ucast=0,
                out_mcast=0,
                out_bcast=0,
                out_disc=0,
                out_err=0,
            ),
            get_rate_errors=[],
        ),
        interfaces.InterfaceWithRates(
            interfaces.Attributes(
                index="5",
                descr="vmnic4",
                alias="vmnic4",
                type="6",
                speed=10000000000,
                oper_status="1",
                phys_address="dQ\x06ðÅÐ",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Rates(
                in_octets=105472,
                in_ucast=2437,
                in_mcast=113,
                in_bcast=208,
                in_disc=0,
                in_err=0,
                out_octets=76800,
                out_ucast=1146,
                out_mcast=0,
                out_bcast=2,
                out_disc=0,
                out_err=0,
            ),
            get_rate_errors=[],
        ),
        interfaces.InterfaceWithRates(
            interfaces.Attributes(
                index="6",
                descr="vmnic5",
                alias="vmnic5",
                type="6",
                speed=10000000000,
                oper_status="1",
                phys_address="dQ\x06ðÅÔ",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Rates(
                in_octets=55296,
                in_ucast=4549,
                in_mcast=113,
                in_bcast=208,
                in_disc=0,
                in_err=0,
                out_octets=759808,
                out_ucast=2178,
                out_mcast=0,
                out_bcast=0,
                out_disc=0,
                out_err=0,
            ),
            get_rate_errors=[],
        ),
    ]


def test_discovery_counters_diskio() -> None:
    assert list(
        esx_vsphere_counters.discover_esx_vsphere_counters_diskio(
            OrderedDict(
                {
                    "disk.read": {"": [(["11", "12", "13"], "kiloBytesPerSecond")]},
                    "disk.numberReadAveraged": {"": [(["110", "140", "150"], "number")]},
                    "disk.write": {"": [(["51", "49", "53"], "kiloBytesPerSecond")]},
                    "disk.numberWriteAveraged": {"": [(["11", "102", "5"], "number")]},
                    "disk.deviceLatency": {"": [(["700", "900", "23"], "millisecond")]},
                }
            )
        )
    ) == [Service(item="SUMMARY")]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_counters_diskio() -> None:
    assert list(
        esx_vsphere_counters.check_esx_vsphere_counters_diskio(
            "SUMMARY",
            {},
            OrderedDict(
                {
                    "disk.read": {"": [(["11", "12", "13"], "kiloBytesPerSecond")]},
                    "disk.numberReadAveraged": {"": [(["110", "140", "150"], "number")]},
                    "disk.write": {"": [(["51", "49", "53"], "kiloBytesPerSecond")]},
                    "disk.numberWriteAveraged": {"": [(["11", "102", "5"], "number")]},
                    "disk.deviceLatency": {"": [(["700", "900", "23"], "millisecond")]},
                }
            ),
        )
    ) == [
        Result(state=State.OK, summary="Read: 12.3 kB/s"),
        Metric("disk_read_throughput", 12288.0),
        Result(state=State.OK, summary="Write: 52.2 kB/s"),
        Metric("disk_write_throughput", 52224.0),
        Result(state=State.OK, notice="Read operations: 133.33/s"),
        Metric("disk_read_ios", 133.33333333333334),
        Result(state=State.OK, notice="Write operations: 39.33/s"),
        Metric("disk_write_ios", 39.333333333333336),
        Result(state=State.OK, summary="Latency: 900 milliseconds"),
        Metric("disk_latency", 0.9),
    ]
