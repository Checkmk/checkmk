#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

# mypy: disallow_untyped_defs
import polyfactory.factories.pydantic_factory
import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.gcp.agent_based import gcp_status
from cmk.plugins.gcp.lib import constants


class IncidentFactory(polyfactory.factories.pydantic_factory.ModelFactory):
    __model__ = gcp_status.Incident


class AgentOutputFactory(polyfactory.factories.pydantic_factory.ModelFactory):
    __model__ = gcp_status.AgentOutput


@pytest.fixture(name="section", scope="module")
def _section() -> gcp_status.Section:
    # This is an agent output, which is edited to only have a single (unedited) incident.
    # https://status.cloud.google.com/incidents.schema.json
    string_table = [
        [
            r"""{
      "discovery_param": {
        "regions": [
          "europe-north1"
        ]
      },
      "health_info": [
        {
          "id": "rZvZvSKVdDHyWh4dZJ8D",
          "number": "15564124031412553730",
          "begin": "2023-03-10T14:09:43+00:00",
          "created": "2023-03-10T14:26:24+00:00",
          "end": "2023-03-10T14:54:50+00:00",
          "modified": "2023-03-10T14:54:50+00:00",
          "external_desc": "Retry errors for Google BigQuery in europe-north1",
          "updates": [
            {
              "created": "2023-03-10T14:26:17+00:00",
              "modified": "2023-03-10T14:26:28+00:00",
              "when": "2023-03-10T14:26:17+00:00",
              "text": "Summary: Retry errors for Google BigQuery in europe-north1\nDescription: We are experiencing an issue with Google BigQuery.\nOur engineering team continues to investigate the issue.\nWe will provide an update by Friday, 2023-03-10 07:30 US/Pacific with current details.\nDiagnosis: Customers may experience retry errors when running DatasetService.*, TableService.*, BigQueryRead.CreateReadSession, BigQueryRead.ReadRows and BigQueryWrite.* commands for Google BigQuery in europe-north1\nWorkaround: Retry requests",
              "status": "SERVICE_INFORMATION",
              "affected_locations": [
                {
                  "title": "Finland (europe-north1)",
                  "id": "europe-north1"
                }
              ]
            }
          ],
          "most_recent_update": {
            "created": "2023-03-10T14:26:17+00:00",
            "modified": "2023-03-10T14:26:28+00:00",
            "when": "2023-03-10T14:26:17+00:00",
            "text": "Summary: Retry errors for Google BigQuery in europe-north1\nDescription: We are experiencing an issue with Google BigQuery.\nOur engineering team continues to investigate the issue.\nWe will provide an update by Friday, 2023-03-10 07:30 US/Pacific with current details.\nDiagnosis: Customers may experience retry errors when running DatasetService.*, TableService.*, BigQueryRead.CreateReadSession, BigQueryRead.ReadRows and BigQueryWrite.* commands for Google BigQuery in europe-north1\nWorkaround: Retry requests",
            "status": "SERVICE_INFORMATION",
            "affected_locations": [
              {
                "title": "Finland (europe-north1)",
                "id": "europe-north1"
              }
            ]
          },
          "status_impact": "SERVICE_INFORMATION",
          "severity": "low",
          "service_key": "9CcrhHUcFevXPSVaSxkf",
          "service_name": "Google BigQuery",
          "affected_products": [
            {
              "title": "Google BigQuery",
              "id": "9CcrhHUcFevXPSVaSxkf"
            }
          ],
          "uri": "incidents/rZvZvSKVdDHyWh4dZJ8D",
          "currently_affected_locations": [
            {
              "title": "Finland (europe-north1)",
              "id": "europe-north1"
            }
          ],
          "previously_affected_locations": []
        }
      ]
    }
    """
        ]
    ]
    return gcp_status.parse(string_table)


def test_parsing(section: gcp_status.Section) -> None:
    assert section.discovery_param == gcp_status.DiscoveryParam(regions=["europe-north1"])
    assert section.data == {
        "Finland": [
            gcp_status.Incident(
                affected_products=[gcp_status.AffectedProduct(title="Google BigQuery")],
                currently_affected_locations=[gcp_status.AffectedLocation(id="europe-north1")],
                external_desc="Retry errors for Google BigQuery in europe-north1",
                uri="incidents/rZvZvSKVdDHyWh4dZJ8D",
            )
        ]
    }


def test_parsing_global() -> None:
    # This is an agent output, which is edited to only have a single (unedited) incident.
    string_table = [
        [
            r"""{
      "discovery_param": {
        "regions": [
          "europe-west3"
        ]
      },
      "health_info": [
        {
          "id": "rZvZvSKVdDHyWh4dZJ8D",
          "number": "15564124031412553730",
          "begin": "2023-03-10T14:09:43+00:00",
          "created": "2023-03-10T14:26:24+00:00",
          "end": "2023-03-10T14:54:50+00:00",
          "modified": "2023-03-10T14:54:50+00:00",
          "external_desc": "Retry errors for Google BigQuery in global",
          "updates": [
            {
              "created": "2023-03-10T14:26:17+00:00",
              "modified": "2023-03-10T14:26:28+00:00",
              "when": "2023-03-10T14:26:17+00:00",
              "text": "Summary: Retry errors for Google BigQuery in global\nDescription: We are experiencing an issue with Google BigQuery.\nOur engineering team continues to investigate the issue.\nWe will provide an update by Friday, 2023-03-10 07:30 US/Pacific with current details.\nDiagnosis: Customers may experience retry errors when running DatasetService.*, TableService.*, BigQueryRead.CreateReadSession, BigQueryRead.ReadRows and BigQueryWrite.* commands for Google BigQuery in global\nWorkaround: Retry requests",
              "status": "SERVICE_INFORMATION",
              "affected_locations": [
                {
                  "title": "Finland (global)",
                  "id": "global"
                }
              ]
            }
          ],
          "most_recent_update": {
            "created": "2023-03-10T14:26:17+00:00",
            "modified": "2023-03-10T14:26:28+00:00",
            "when": "2023-03-10T14:26:17+00:00",
            "text": "Summary: Retry errors for Google BigQuery in global\nDescription: We are experiencing an issue with Google BigQuery.\nOur engineering team continues to investigate the issue.\nWe will provide an update by Friday, 2023-03-10 07:30 US/Pacific with current details.\nDiagnosis: Customers may experience retry errors when running DatasetService.*, TableService.*, BigQueryRead.CreateReadSession, BigQueryRead.ReadRows and BigQueryWrite.* commands for Google BigQuery in global\nWorkaround: Retry requests",
            "status": "SERVICE_INFORMATION",
            "affected_locations": [
              {
                "title": "Finland (global)",
                "id": "global"
              }
            ]
          },
          "status_impact": "SERVICE_INFORMATION",
          "severity": "low",
          "service_key": "9CcrhHUcFevXPSVaSxkf",
          "service_name": "Google BigQuery",
          "affected_products": [
            {
              "title": "Google BigQuery",
              "id": "9CcrhHUcFevXPSVaSxkf"
            }
          ],
          "uri": "incidents/rZvZvSKVdDHyWh4dZJ8D",
          "currently_affected_locations": [
            {
              "title": "Finland (global)",
              "id": "global"
            }
          ],
          "previously_affected_locations": []
        }
      ]
    }
    """
        ]
    ]
    section_global = gcp_status.parse(string_table)
    assert section_global.discovery_param == gcp_status.DiscoveryParam(regions=["europe-west3"])
    assert section_global.data == {
        "Global": [
            gcp_status.Incident(
                affected_products=[gcp_status.AffectedProduct(title="Google BigQuery")],
                currently_affected_locations=[gcp_status.AffectedLocation(id="global")],
                external_desc="Retry errors for Google BigQuery in global",
                uri="incidents/rZvZvSKVdDHyWh4dZJ8D",
            )
        ]
    }


def test_no_indicents() -> None:
    discovery_param = gcp_status.DiscoveryParam(regions=["us-east"])
    section = gcp_status.Section(discovery_param=discovery_param, data={})
    results = list(gcp_status.check(item=discovery_param.regions[0], section=section))
    assert results == [gcp_status._NO_ISSUES]


def test_one_incident_per_region() -> None:
    incident = IncidentFactory.build(
        currently_affected_locations=[
            gcp_status.AffectedLocation(id="asia-east1"),
            gcp_status.AffectedLocation(id="asia-east2"),
            gcp_status.AffectedLocation(id="asia-northeast1"),
        ],
    )
    agent_output = AgentOutputFactory.build(health_info=[incident])
    section = gcp_status.parse([[agent_output.model_dump_json(by_alias=True)]])
    assert all(
        constants.RegionMap[l.id_] in section.data for l in incident.currently_affected_locations
    )


def test_result_per_incident() -> None:
    incident_count = 3
    item = constants.RegionMap["asia-east1"]
    section = gcp_status.Section(
        discovery_param=gcp_status.DiscoveryParam(regions=[]),
        data={item: IncidentFactory.batch(size=incident_count)},
    )
    results = list(gcp_status.check(item, section=section))
    assert sum(isinstance(r, Result) and r.state == State.CRIT for r in results) == incident_count


def test_result_shows_up_correctly(section: gcp_status.Section) -> None:
    item = constants.RegionMap["europe-north1"]
    results = list(gcp_status.check(item, section=section))
    assert results == [
        Result(
            state=State.CRIT,
            summary="Retry errors for Google BigQuery in europe-north1",
            details="Products: Google BigQuery \n https://status.cloud.google.com/incidents/rZvZvSKVdDHyWh4dZJ8D",
        )
    ]
