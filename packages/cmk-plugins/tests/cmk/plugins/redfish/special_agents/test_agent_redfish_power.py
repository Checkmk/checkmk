#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any, no-untyped-call"
"""Service root handling of the Redfish power special agent: rack PDUs must be
found even when the service root does not advertise ``PowerEquipment``."""

from typing import Any

import pytest

from cmk.plugins.redfish.special_agents import agent_redfish_power

# Service root as served by a PANDUIT PDU (firmware 5.2.5): no `PowerEquipment`,
# instead a non-standard `PowerDistribution` link straight to the PDU collection.
PANDUIT_SERVICE_ROOT: dict[str, Any] = {
    "@odata.id": "/redfish/v1",
    "@odata.type": "#ServiceRoot.v1_16_1.ServiceRoot",
    "Id": "RootService",
    "Name": "Redfish Root Service",
    "RedfishVersion": "1.6.0",
    "PowerDistribution": {"@odata.id": "/redfish/v1/PowerEquipment/RackPDUs"},
    "Managers": {"@odata.id": "/redfish/v1/Managers"},
    "AccountService": {"@odata.id": "/redfish/v1/AccountService"},
    "EventService": {"@odata.id": "/redfish/v1/EventService"},
    "SessionService": {"@odata.id": "/redfish/v1/SessionService"},
}

MANAGER_COLLECTION: dict[str, Any] = {
    "@odata.id": "/redfish/v1/Managers/",
    "@odata.type": "#ManagerCollection.ManagerCollection",
    "Name": "Manager Collection",
    "Oem": {},
    "Members@odata.count": 1,
    "Members": [{"@odata.id": "/redfish/v1/Managers/manager"}],
}

MANAGER: dict[str, Any] = {
    "@odata.id": "/redfish/v1/Managers/manager",
    "@odata.type": "#Manager.v1_19_0.Manager",
    "Id": "manager",
    "Name": "Manager",
    "FirmwareVersion": "5.2.5",
    "PowerState": "On",
    "Status": {"State": "Enabled", "Health": "OK"},
}

RACKPDU_COLLECTION: dict[str, Any] = {
    "@odata.type": "#RackPDUCollection.RackPDUCollection",
    "Members@odata.count": 1,
    "Members": [{"@odata.id": "/redfish/v1/PowerEquipment/RackPDUs/1"}],
}

RACKPDU: dict[str, Any] = {
    "@odata.type": "#PowerDistribution.v1_2_2.PowerDistribution",
    "Id": "1",
    "Name": "PDU 1",
    "Status": {"Health": "OK", "State": "Enabled"},
}


class _Response:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.dict = payload


class _FakeClient:
    """Minimal stand-in for redfish.rest.v1.HttpClient."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self._routes = routes
        self.requested: list[str] = []

    def get(self, url: str, _args: Any = None) -> _Response:
        self.requested.append(url)
        if url not in self._routes:
            return _Response(404, {})
        return _Response(200, self._routes[url])


def _panduit_routes() -> dict[str, Any]:
    return {
        "/redfish/v1": PANDUIT_SERVICE_ROOT,
        "/redfish/v1/Managers": MANAGER_COLLECTION,
        "/redfish/v1/Managers/manager": MANAGER,
        "/redfish/v1/PowerEquipment/RackPDUs": RACKPDU_COLLECTION,
        "/redfish/v1/PowerEquipment/RackPDUs/1": RACKPDU,
    }


POWER_EQUIPMENT: dict[str, Any] = {
    "@odata.id": "/redfish/v1/PowerEquipment",
    "@odata.type": "#PowerEquipment.v1_2_0.PowerEquipment",
    "Id": "PowerEquipment",
    "Name": "Power Equipment",
    "RackPDUs": {"@odata.id": "/redfish/v1/PowerEquipment/RackPDUs"},
}


def test_advertised_power_equipment_link_is_followed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The advertised link is used verbatim, not a hardcoded standard path."""
    routes = _panduit_routes()
    routes["/redfish/v1"] = {
        **{k: v for k, v in PANDUIT_SERVICE_ROOT.items() if k != "PowerDistribution"},
        "PowerEquipment": {"@odata.id": "/redfish/v1/Oem/PowerEquipment"},
    }
    routes["/redfish/v1/Oem/PowerEquipment"] = POWER_EQUIPMENT
    client = _FakeClient(routes)

    assert agent_redfish_power.get_information(client) == 0

    assert "/redfish/v1/Oem/PowerEquipment" in client.requested
    assert "/redfish/v1/PowerEquipment" not in client.requested

    out = capsys.readouterr().out
    assert "<<<redfish_system:sep(0)>>>" in out
    assert "<<<redfish_rackpdus:sep(0)>>>" in out
    assert "PDU 1" in out


def test_power_distribution_service_root_does_not_abort(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A service root without `PowerEquipment` must not end the run."""
    client = _FakeClient(_panduit_routes())

    assert agent_redfish_power.get_information(client) == 0

    out = capsys.readouterr().out
    assert "<<<redfish_rackpdus:sep(0)>>>" in out
    assert "PDU 1" in out


def test_power_distribution_service_root_is_probed_for_power_equipment() -> None:
    """The standard path is tried before falling back to the vendor link."""
    client = _FakeClient(_panduit_routes())

    agent_redfish_power.get_information(client)

    assert "/redfish/v1/PowerEquipment" in client.requested


def test_probe_wins_over_power_distribution(capsys: pytest.CaptureFixture[str]) -> None:
    """Devices that serve PowerEquipment without advertising it use that resource."""
    routes = _panduit_routes()
    routes["/redfish/v1/PowerEquipment"] = POWER_EQUIPMENT
    client = _FakeClient(routes)

    agent_redfish_power.get_information(client)

    # The resource is fetched once - the probe must not cost a second request.
    assert client.requested.count("/redfish/v1/PowerEquipment") == 1

    out = capsys.readouterr().out
    assert "<<<redfish_system:sep(0)>>>" in out
    assert "<<<redfish_rackpdus:sep(0)>>>" in out


def test_power_distribution_fallback_emits_no_system_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The synthesised mapping is not a PowerEquipment resource, so it must not
    reach the redfish_system section - it would discover a nameless service."""
    client = _FakeClient(_panduit_routes())

    agent_redfish_power.get_information(client)

    assert "<<<redfish_system:sep(0)>>>" not in capsys.readouterr().out


def test_empty_power_equipment_resource_emits_no_system_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A PowerEquipment resource served as an empty body has nothing to report -
    emitting it would discover a nameless service."""
    routes = _panduit_routes()
    routes["/redfish/v1"] = {
        **{k: v for k, v in PANDUIT_SERVICE_ROOT.items() if k != "PowerDistribution"},
        "PowerEquipment": {"@odata.id": "/redfish/v1/PowerEquipment"},
    }
    routes["/redfish/v1/PowerEquipment"] = {}
    client = _FakeClient(routes)

    assert agent_redfish_power.get_information(client) == 0
    assert "<<<redfish_system:sep(0)>>>" not in capsys.readouterr().out


def test_empty_rackpdu_collection_does_not_crash(capsys: pytest.CaptureFixture[str]) -> None:
    """A PDU collection without members must not abort the run."""
    routes = _panduit_routes()
    routes["/redfish/v1/PowerEquipment/RackPDUs"] = {
        "@odata.type": "#RackPDUCollection.RackPDUCollection",
        "Members@odata.count": 0,
        "Members": [],
    }
    client = _FakeClient(routes)

    assert agent_redfish_power.get_information(client) == 0
    assert "<<<redfish_rackpdus:sep(0)>>>" not in capsys.readouterr().out


def test_unreachable_rackpdu_collection_does_not_crash() -> None:
    """A PDU collection that cannot be fetched must not abort the run."""
    routes = _panduit_routes()
    del routes["/redfish/v1/PowerEquipment/RackPDUs"]
    client = _FakeClient(routes)

    assert agent_redfish_power.get_information(client) == 0


def test_service_root_without_any_power_link_still_aborts() -> None:
    """Devices that are genuinely not power equipment keep the clear error."""
    client = _FakeClient(
        {
            "/redfish/v1": {
                "@odata.id": "/redfish/v1",
                "@odata.type": "#ServiceRoot.v1_16_1.ServiceRoot",
                "Managers": {"@odata.id": "/redfish/v1/Managers"},
            },
            "/redfish/v1/Managers": MANAGER_COLLECTION,
            "/redfish/v1/Managers/manager": MANAGER,
        }
    )

    with pytest.raises(
        agent_redfish_power.CannotRecover, match="missing PowerEquipment information"
    ):
        agent_redfish_power.get_information(client)
