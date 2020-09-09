#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json


def test_openapi_get_bi_packs(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    response = wsgi_app.get(base + '/domain-types/bi_pack/collections/all')
    packs = json.loads(response.text)
    assert packs["domainType"] == "bi_pack"
    assert len(packs["value"]) == 1
    assert packs["value"][0]["title"] == "Default Pack"


def test_openapi_get_bi_pack(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    pack_id = "default"
    response = wsgi_app.get(base + '/objects/bi_pack/%s' % pack_id, status=200)
    pack = json.loads(response.text)
    assert pack["id"] == pack_id
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1


def test_openapi_get_bi_aggregation(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    aggr_id = "default_aggregation"
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggregation = json.loads(response.text)
    for required_key in [
            "aggregation_visualization",
            "computation_options",
            "groups",
            "id",
            "node",
            "pack_id",
    ]:
        assert required_key in aggregation

    assert aggregation["id"] == aggr_id


def test_openapi_get_bi_rule(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    rule_id = "applications"
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)
    for required_key in [
            "computation_options",
            "id",
            "node_visualization",
            "nodes",
            "pack_id",
            "properties",
    ]:
        assert required_key in rule

    assert rule["id"] == rule_id


def test_openapi_modify_bi_aggregation(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    aggr_id = "default_aggregation"
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggregation = json.loads(response.text)
    assert not aggregation["computation_options"]["disabled"]
    assert not aggregation["computation_options"]["escalate_downtimes_as_warn"]

    # Modify and send back
    aggregation["computation_options"]["disabled"] = True
    aggregation["computation_options"]["escalate_downtimes_as_warn"] = True
    response = wsgi_app.put(base + '/objects/bi_aggregation/%s' % aggr_id,
                            content_type='application/json',
                            params=json.dumps(aggregation),
                            status=200)

    # Verify changed configuration
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggregation = json.loads(response.text)
    assert aggregation["computation_options"]["disabled"]
    assert aggregation["computation_options"]["escalate_downtimes_as_warn"]


def test_openapi_modify_bi_rule(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    rule_id = "applications"
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)
    rule["params"]["arguments"].append("OTHERARGUMENT")

    # Modify and send back
    response = wsgi_app.put(base + '/objects/bi_rule/%s' % rule_id,
                            content_type='application/json',
                            params=json.dumps(rule),
                            status=200)

    # Verify changed configuration
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)
    assert "OTHERARGUMENT" in rule["params"]["arguments"]


def test_openapi_clone_bi_aggregation(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    aggr_id = "default_aggregation"
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggr = json.loads(response.text)

    clone_id = "cloned_aggregation"
    aggr["id"] = clone_id

    # Modify and send back
    response = wsgi_app.put(base + '/objects/bi_aggregation/%s' % aggr_id,
                            content_type='application/json',
                            params=json.dumps(aggr),
                            status=200)

    # Verify cloned_rule configuration
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % clone_id, status=200)
    cloned_aggr = json.loads(response.text)
    assert cloned_aggr["id"] == clone_id

    # Verify changed pack size
    response = wsgi_app.get(base + '/objects/bi_pack/default', status=200)
    pack = json.loads(response.text)
    assert len(pack["members"]["aggregations"]["value"]) == 2


def test_openapi_clone_bi_rule(
    wsgi_app,
    with_automation_user,
    bi_packs_sample_config,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    rule_id = "applications"
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)

    clone_id = "appliations_clone"
    rule["id"] = clone_id

    # Modify and send back
    response = wsgi_app.put(base + '/objects/bi_rule/%s' % rule_id,
                            content_type='application/json',
                            params=json.dumps(rule),
                            status=200)

    # Verify cloned_rule configuration
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % clone_id, status=200)
    cloned_rule = json.loads(response.text)
    assert cloned_rule["id"] == clone_id

    # Verify changed pack size
    response = wsgi_app.get(base + '/objects/bi_pack/default', status=200)
    pack = json.loads(response.text)
    assert len(pack["members"]["rules"]["value"]) == 13
