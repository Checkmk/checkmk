#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.special_agents.agent_vsphere import eval_multipath_info, fetch_virtual_machines


def _build_id(lun_id):
    # Taken from https://kb.vmware.com/s/article/2078730
    assert len(lun_id) == 32 or len(lun_id) == 0
    uuid_type = "02"
    device_type = "00"
    lun_number = "00"
    reserved = "0000"
    unique_hash = "695343534944"

    return f"{uuid_type}{device_type}{lun_number}{reserved}{lun_id}{unique_hash}"


VALID_LUN_ID = "12344a12345b4b0000333a4b00000320"
VALID_PATH = "aaaaa1:AA:AA:AA"
MULTIPATH_PROPSET = (
    "<id>%s</id>"
    "<path>"
    f"<key>key-vim.host.MultipathInfo.Path-{VALID_PATH}</key>"
    f"<name>{VALID_PATH}</name>"
    "<pathState>active</pathState>"
    "<state>active</state>"
    "<isWorkingPath>true</isWorkingPath>"
    "<adapter>key-vim.host.BlockHba-vmhba2</adapter>"
    "<lun>key-vim.host.MultipathInfo.LogicalUnit-123456789</lun>"
    '<transport xsi:type="HostBlockAdapterTargetTransport"></transport>'
    "</path>"
)
PROP_NAME = "foo"


@pytest.mark.parametrize(
    "propset, expected",
    [
        (
            MULTIPATH_PROPSET % _build_id(VALID_LUN_ID),
            ({PROP_NAME: [f"{VALID_LUN_ID} {VALID_PATH} active"]}, {}),
        ),
        (
            MULTIPATH_PROPSET % _build_id(""),
            ({}, {}),
        ),
    ],
)
def test_eval_multipath_info(propset, expected):
    assert eval_multipath_info("", PROP_NAME, propset) == expected


def test_cloning_vm_is_processed(mocker):
    """
    VMs that are in the process of being cloned do not define runtime.host.
    Make sure that this does not lead to a KeyError.
    """
    data = (
        # this is thinned out data
        '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenc="http://schemas.xmlsoa'
        'p.org/soap/encoding/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="h'
        'ttp://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soap'
        'env:Body><RetrievePropertiesExResponse xmlns="urn:vim25"><returnval><token>0</token><objects'
        '><obj type="VirtualMachine">vm-111</obj><propSet><name>config.datastoreUrl</name><val xsi:ty'
        'pe="ArrayOfVirtualMachineConfigInfoDatastoreUrlPair"><VirtualMachineConfigInfoDatastoreUrlPa'
        'ir xsi:type="VirtualMachineConfigInfoDatastoreUrlPair"><name>Storage</name><url>/vmfs/volume'
        "s/11111111-22222222-0000-000000000000</url></VirtualMachineConfigInfoDatastoreUrlPair></val>"
        '</propSet><propSet><name>config.guestFullName</name><val xsi:type="xsd:string">Red Hat Enter'
        "prise Linux 7 (64 Bit)</val></propSet><propSet><name>config.hardware.device</name><val xsi:t"
        'ype="ArrayOfVirtualDevice"><VirtualDevice xsi:type="VirtualIDEController"><key>200</key><dev'
        "iceInfo><label>IDE 0</label><summary>IDE 0</summary></deviceInfo><busNumber>0</busNumber></V"
        'irtualDevice></val></propSet><propSet><name>config.hardware.memoryMB</name><val xsi:type="xs'
        'd:int">33333</val></propSet><propSet><name>config.uuid</name><val xsi:type="xsd:string">1111'
        "1111-2222-3333-4444-555555555555</val></propSet><propSet><name>guestHeartbeatStatus</name><v"
        'al xsi:type="ManagedEntityStatus">green</val></propSet><propSet><name>name</name><val xsi:ty'
        'pe="xsd:string">AAA-BBBBBBB</val></propSet><propSet><name>runtime.host</name><val type="Host'
        'System" xsi:type="ManagedObjectReference">host-222</val></propSet></objects><objects><obj ty'
        'pe="VirtualMachine">vm-888</obj><propSet><name>guestHeartbeatStatus</name><val xsi:type="Man'
        'agedEntityStatus">gray</val></propSet><propSet><name>name</name><val xsi:type="xsd:string">A'
        'AA-BBBB-CCCCC</val></propSet><propSet><name>runtime.powerState</name><val xsi:type="VirtualM'
        'achinePowerState">poweredOff</val></propSet></objects></returnval></RetrievePropertiesExResp'
        "onse></soapenv:Body></soapenv:Envelope>"
    )

    connection = mocker.Mock()
    connection.query_server = mocker.Mock(return_value=data)
    opt = mocker.Mock()
    opt.skip_placeholder_vm = False

    result = fetch_virtual_machines(connection, hostsystems={}, datastores={}, opt=opt)

    assert result == (
        {
            "AAA-BBBB-CCCCC": {
                "guestHeartbeatStatus": "gray",
                "name": "AAA-BBBB-CCCCC",
                "runtime.powerState": "poweredOff",
            },
            "AAA-BBBBBBB": {
                "config.datastoreUrl": "name Storage",
                "config.guestFullName": "Red Hat Enterprise Linux 7 (64 Bit)",
                "config.hardware.device": "",
                "config.hardware.memoryMB": "33333",
                "config.uuid": "11111111-2222-3333-4444-555555555555",
                "guestHeartbeatStatus": "green",
                "name": "AAA-BBBBBBB",
                "runtime.host": "host-222",
            },
        },
        {"host-222": ["AAA-BBBBBBB"]},
    )
