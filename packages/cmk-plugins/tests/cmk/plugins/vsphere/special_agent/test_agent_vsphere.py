#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import override
from unittest.mock import MagicMock, patch

import pytest

from cmk.plugins.vsphere.special_agent.agent_vsphere import (
    convert_hostname,
    ESXConnection,
    ESXSession,
    eval_datastores,
    eval_multipath_info,
    eval_snapshot_list,
    fetch_virtual_machines,
    get_hostsystem_power_states,
    get_section_snapshot_summary,
    get_vm_power_states,
)
from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter, Storage


def _build_id(lun_id: str) -> str:
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
def test_eval_multipath_info(
    propset: str, expected: tuple[Mapping[str, Sequence[str]], Mapping[object, object]]
) -> None:
    assert eval_multipath_info("", PROP_NAME, propset) == expected


def test_postsoap_encodes_body_as_utf8() -> None:
    session = ESXSession("vcenter.example.com", 443, cert_check=False)

    payload = (
        '<ns1:Login xsi:type="ns1:LoginRequestType">'
        "  <ns1:userName>user</ns1:userName>"
        "  <ns1:password>pa§§word</ns1:password>"
        "</ns1:Login>"
    )

    with patch("requests.Session.post", return_value=MagicMock()) as mock_post:
        session.postsoap(payload)

    sent_data = mock_post.call_args.kwargs["data"]
    assert isinstance(sent_data, bytes)
    assert sent_data.decode("utf-8")
    assert "pa§§word".encode() in sent_data


class FakeConnection(ESXConnection):
    """Encapsulates the API calls to the ESX system"""

    def __init__(self) -> None:
        pass

    @override
    def query_server(self, method: str, **kwargs: str) -> str:
        return (
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


_STORE_AGENT = "agent_vsphere"
_STORE_HOST = "vcenter.example.com"


class StoreBackedConnection(ESXConnection):
    """Connection wired to a real Storage, without performing any vCenter I/O."""

    def __init__(self) -> None:
        self._store = Storage(_STORE_AGENT, _STORE_HOST)
        self._perf_samples = None

    def read_stored_float(self, key: str, default: float) -> float:
        return self._read_stored_float(key, default)


class TestStoreBackedReads:
    @pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
    def patch_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))

    def test_read_stored_float_falls_back_on_empty_content(self) -> None:
        Storage(_STORE_AGENT, _STORE_HOST).write("timer", "")
        connection = StoreBackedConnection()

        result = connection.read_stored_float("timer", 12.5)

        assert result == 12.5

    def test_read_stored_float_falls_back_on_unparsable_content(self) -> None:
        Storage(_STORE_AGENT, _STORE_HOST).write("timer", "not-a-float")
        connection = StoreBackedConnection()

        result = connection.read_stored_float("timer", 12.5)

        assert result == 12.5

    def test_read_stored_float_parses_valid_content(self) -> None:
        Storage(_STORE_AGENT, _STORE_HOST).write("timer", "123.0")
        connection = StoreBackedConnection()

        result = connection.read_stored_float("timer", 12.5)

        assert result == 123.0

    def test_perf_samples_does_not_crash_on_empty_timer_store(self) -> None:
        store = Storage(_STORE_AGENT, _STORE_HOST)
        store.write("timer", "")

        perf_samples = StoreBackedConnection().perf_samples

        assert perf_samples >= 1
        assert float(store.read("timer", ""))


def test_cloning_vm_is_processed() -> None:
    """
    VMs that are in the process of being cloned do not define runtime.host.
    Make sure that this does not lead to a KeyError.
    """

    opt = argparse.Namespace(skip_placeholder_vm=False, vm_piggyname=None, spaces="underscore")

    result = fetch_virtual_machines(FakeConnection(), hostsystems={}, datastores={}, opt=opt)

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


@pytest.mark.parametrize(
    "virtual_machines, systime, expected_output",
    [
        pytest.param(
            {
                "vm_name": {
                    "name": "vm_name",
                    "snapshot.rootSnapshotList": "871 1605626114 poweredOn SnapshotName|834 1605632160 poweredOff Snapshotname2",
                }
            },
            1605636114,
            [
                "<<<esx_vsphere_snapshots_summary:sep(0)>>>",
                '{"time": 1605626114, "systime": 1605636114, "state": "poweredOn", "name": "SnapshotName", "vm": "vm_name"}',
                '{"time": 1605632160, "systime": 1605636114, "state": "poweredOff", "name": "Snapshotname2", "vm": "vm_name"}',
            ],
            id="There are two snapshots available. For every available snapshot, information about the creation time, state, name and vm_name is provided.",
        ),
        pytest.param(
            {"vm_name": {"name": "vm_name"}},
            1605636114,
            ["<<<esx_vsphere_snapshots_summary:sep(0)>>>"],
            id="There are no snapshots available and because of that an empty section is created.",
        ),
        pytest.param(
            {
                "vm_name": {
                    "name": "vm_name",
                    "snapshot.rootSnapshotList": "871 1605626114 poweredOn SnapshotName",
                }
            },
            1605636114,
            [
                "<<<esx_vsphere_snapshots_summary:sep(0)>>>",
                '{"time": 1605626114, "systime": 1605636114, "state": "poweredOn", "name": "SnapshotName", "vm": "vm_name"}',
            ],
            id="There is only one snapshot available. Same behaviour as when there are multiple snapshots available.",
        ),
        pytest.param(
            {
                "vm_name": {
                    "name": "vm_name",
                    "snapshot.rootSnapshotList": "871 1605626114 poweredOn SnapshotName",
                }
            },
            None,
            [
                "<<<esx_vsphere_snapshots_summary:sep(0)>>>",
                '{"time": 1605626114, "systime": null, "state": "poweredOn", "name": "SnapshotName", "vm": "vm_name"}',
            ],
            id="Systime not available",
        ),
    ],
)
def test_get_section_snapshot_summary(
    virtual_machines: Mapping[str, Mapping[str, str]],
    systime: int | None,
    expected_output: Sequence[str],
) -> None:
    assert get_section_snapshot_summary(virtual_machines, systime) == expected_output


def test_ipv6_addresses_are_bracketed_in_the_service_url() -> None:
    session = ESXSession("fd00::10", 443, cert_check=False)

    with patch("requests.Session.post", return_value=MagicMock()) as mock_post:
        session.postsoap("<ns1:CurrentTime/>")

    assert mock_post.call_args.args[0] == "https://[fd00::10]:443/sdk"


def test_certificate_server_name_is_verified_with_hostname_validation() -> None:
    session = ESXSession("10.0.0.1", 443, cert_check="vcenter.example.com")

    adapter = session.get_adapter("https://10.0.0.1:443/sdk")

    assert isinstance(adapter, HostnameValidationAdapter)


def test_trace_recording_redacts_login_requests() -> None:
    login_request = b"<ns1:Login><ns1:password>secret</ns1:password></ns1:Login>"

    assert ESXConnection.filter_request_body(login_request) == b"login request filtered out"


def test_trace_recording_keeps_other_requests() -> None:
    request = b"<ns1:CurrentTime/>"

    assert ESXConnection.filter_request_body(request) == request


def _options(**overrides: object) -> argparse.Namespace:
    options: dict[str, object] = {
        "direct": False,
        "spaces": "underscore",
        "vm_pwr_display": "host",
        "host_pwr_display": "host",
        "hostname": None,
    }
    return argparse.Namespace(**{**options, **overrides})


OBJECTS_HEADER = "<<<esx_vsphere_objects:sep(9)>>>"
VMS = {"web-01": {"name": "web-01", "runtime.host": "esx01", "runtime.powerState": "poweredOn"}}
VM_LINE = "virtualmachine\tweb-01\tesx01\tpoweredOn"
HOST_PROPERTIES = {"host-10": {"name": ["esx01"], "runtime.powerState": ["poweredOn"]}}
HOST_LINE = "hostsystem\tesx01\t\tpoweredOn"


def test_vm_power_state_is_reported_on_the_queried_system_by_default() -> None:
    section = get_vm_power_states(VMS, {}, _options())

    assert section == ["<<<<>>>>", OBJECTS_HEADER, VM_LINE, "<<<<>>>>"]


def test_vm_power_state_is_additionally_piggybacked_on_the_vm() -> None:
    section = get_vm_power_states(VMS, {}, _options(vm_pwr_display="vm"))

    assert section == [
        "<<<<web-01>>>>",
        OBJECTS_HEADER,
        VM_LINE,
        "<<<<>>>>",
        OBJECTS_HEADER,
        VM_LINE,
        "<<<<>>>>",
    ]


def test_vm_power_state_is_additionally_piggybacked_on_the_esx_host() -> None:
    section = get_vm_power_states(VMS, {}, _options(vm_pwr_display="esxhost"))

    assert section == [
        "<<<<esx01>>>>",
        OBJECTS_HEADER,
        VM_LINE,
        "<<<<>>>>",
        OBJECTS_HEADER,
        VM_LINE,
        "<<<<>>>>",
    ]


def test_esx_host_piggyback_of_vm_power_states_is_skipped_for_direct_queries() -> None:
    section = get_vm_power_states(VMS, {}, _options(vm_pwr_display="esxhost", direct=True))

    assert section == ["<<<<>>>>", OBJECTS_HEADER, VM_LINE, "<<<<>>>>"]


def test_templates_are_reported_as_template_objects() -> None:
    templates = {"tmpl-01": {**VMS["web-01"], "name": "tmpl-01", "config.template": "true"}}

    section = get_vm_power_states(templates, {}, _options())

    assert "template\ttmpl-01\tesx01\tpoweredOn" in section


def test_host_power_state_is_reported_on_the_queried_system_by_default() -> None:
    section = get_hostsystem_power_states({}, {}, HOST_PROPERTIES, _options())

    assert section == ["<<<<>>>>", OBJECTS_HEADER, HOST_LINE, "<<<<>>>>"]


def test_host_power_state_is_additionally_piggybacked_on_the_esx_host() -> None:
    section = get_hostsystem_power_states(
        {}, {}, HOST_PROPERTIES, _options(host_pwr_display="esxhost")
    )

    assert section == [
        "<<<<>>>>",
        OBJECTS_HEADER,
        HOST_LINE,
        "<<<<esx01>>>>",
        OBJECTS_HEADER,
        HOST_LINE,
        "<<<<>>>>",
    ]


def test_host_power_state_is_piggybacked_on_each_vm_running_on_the_host() -> None:
    section = get_hostsystem_power_states(VMS, {}, HOST_PROPERTIES, _options(host_pwr_display="vm"))

    assert section == ["<<<<web-01>>>>", OBJECTS_HEADER, HOST_LINE, "<<<<>>>>"]


def test_direct_queries_report_the_host_power_state_under_the_configured_name() -> None:
    section = get_hostsystem_power_states(
        {}, {}, HOST_PROPERTIES, _options(direct=True, hostname="esx-alias")
    )

    assert "hostsystem\tesx-alias\t\tpoweredOn" in section


def test_configured_host_name_is_not_used_when_displaying_the_state_on_vms() -> None:
    section = get_hostsystem_power_states(
        VMS, {}, HOST_PROPERTIES, _options(direct=True, hostname="esx-alias", host_pwr_display="vm")
    )

    assert section == ["<<<<web-01>>>>", OBJECTS_HEADER, HOST_LINE, "<<<<>>>>"]


def test_spaces_in_host_names_are_replaced_by_underscores() -> None:
    assert convert_hostname("esx host 01", _options(spaces="underscore")) == "esx_host_01"


def test_host_names_are_cut_after_the_first_space_on_request() -> None:
    assert convert_hostname("esx host 01", _options(spaces="cut")) == "esx"


def _snapshot_tree(name: str, snapshot_id: int, created: str) -> str:
    return (
        f"<name>{name}</name><description></description><id>{snapshot_id}</id>"
        f"<createTime>{created}</createTime><state>poweredOff</state>"
    )


def test_snapshots_are_serialised_with_epoch_creation_times() -> None:
    serialised = eval_snapshot_list(_snapshot_tree("Before patch", 1, "2024-03-01T10:00:00Z"), {})

    assert serialised == "1 1709287200 poweredOff Before patch"


def test_unparsable_snapshot_creation_times_fall_back_to_zero() -> None:
    serialised = eval_snapshot_list(_snapshot_tree("Before patch", 1, "unknown"), {})

    assert serialised == "1 0 poweredOff Before patch"


def test_multiple_snapshots_are_joined_with_pipes() -> None:
    tree = _snapshot_tree("first", 1, "2024-03-01T10:00:00Z") + _snapshot_tree(
        "second", 2, "2024-03-02T10:00:00Z"
    )

    serialised = eval_snapshot_list(tree, {})

    assert serialised == "1 1709287200 poweredOff first|2 1709373600 poweredOff second"


def test_pipes_in_snapshot_names_are_replaced_to_keep_the_separator_unambiguous() -> None:
    serialised = eval_snapshot_list(_snapshot_tree("before|after", 1, "2024-03-01T10:00:00Z"), {})

    assert serialised == "1 1709287200 poweredOff before after"


def test_vm_datastores_carry_the_details_of_known_datastores() -> None:
    datastores = {
        "datastore-20": {"name": "ds1", "summary.capacity": "100", "summary.freeSpace": "40"}
    }

    serialised = eval_datastores("<name>ds1</name><url>/vmfs/volumes/x/</url>", datastores)

    assert serialised == "name ds1|capacity 100|freeSpace 40"


def test_unknown_vm_datastores_are_reported_by_name_only() -> None:
    serialised = eval_datastores("<name>ds9</name><url>/vmfs/volumes/x/</url>", {})

    assert serialised == "name ds9"
