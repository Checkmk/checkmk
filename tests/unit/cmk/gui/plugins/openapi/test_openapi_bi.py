#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.utils.exceptions import MKGeneralException


def test_openapi_get_bi_packs(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    response = wsgi_app.get(base + '/domain-types/bi_pack/collections/all')
    packs = json.loads(response.text)
    assert packs["domainType"] == "bi_pack"
    assert len(packs["value"]) == 1
    assert packs["value"][0]["title"] == "Default Pack"


def test_openapi_get_bi_pack(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    pack_id = "default"
    response = wsgi_app.get(base + '/objects/bi_pack/%s' % pack_id, status=200)
    pack = json.loads(response.text)
    assert pack["id"] == pack_id
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1


def test_openapi_get_bi_aggregation(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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


def test_openapi_get_bi_rule(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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


def test_openapi_modify_bi_aggregation(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    aggr_id = "default_aggregation"
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggregation = json.loads(response.text)
    assert aggregation["computation_options"]["disabled"]
    assert not aggregation["computation_options"]["escalate_downtimes_as_warn"]

    # Modify and send back
    aggregation["computation_options"]["disabled"] = False
    aggregation["computation_options"]["escalate_downtimes_as_warn"] = True
    wsgi_app.put(base + '/objects/bi_aggregation/%s' % aggr_id,
                 content_type='application/json',
                 params=json.dumps(aggregation),
                 status=200)

    # Verify changed configuration
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggregation = json.loads(response.text)
    assert not aggregation["computation_options"]["disabled"]
    assert aggregation["computation_options"]["escalate_downtimes_as_warn"]


def test_openapi_modify_bi_rule(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    rule_id = "applications"
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)
    rule["params"]["arguments"].append("OTHERARGUMENT")

    # Modify and send back
    wsgi_app.put(base + '/objects/bi_rule/%s' % rule_id,
                 content_type='application/json',
                 params=json.dumps(rule),
                 status=200)

    # Verify changed configuration
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)
    assert "OTHERARGUMENT" in rule["params"]["arguments"]


def test_openapi_clone_bi_aggregation(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    aggr_id = "default_aggregation"
    response = wsgi_app.get(base + '/objects/bi_aggregation/%s' % aggr_id, status=200)
    aggr = json.loads(response.text)

    clone_id = "cloned_aggregation"

    # Check invalid POST request on existing id
    wsgi_app.post(base + '/objects/bi_aggregation/%s' % aggr_id,
                  content_type='application/json',
                  params=json.dumps(aggr),
                  status=404)

    # Check invalid PUT request on new id
    wsgi_app.put(base + '/objects/bi_aggregation/%s' % clone_id,
                 content_type='application/json',
                 params=json.dumps(aggr),
                 status=404)

    # Save config under different id
    wsgi_app.post(base + '/objects/bi_aggregation/%s' % clone_id,
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


def test_openapi_clone_bi_rule(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    rule_id = "applications"
    response = wsgi_app.get(base + '/objects/bi_rule/%s' % rule_id, status=200)
    rule = json.loads(response.text)

    clone_id = "applications_clone"

    # Check invalid POST request on existing id
    wsgi_app.post(base + '/objects/bi_rule/%s' % rule_id,
                  content_type='application/json',
                  params=json.dumps(rule),
                  status=404)

    # Check invalid PUT request on new id
    wsgi_app.put(base + '/objects/bi_rule/%s' % clone_id,
                 content_type='application/json',
                 params=json.dumps(rule),
                 status=404)

    # Save config under different id
    wsgi_app.post(base + '/objects/bi_rule/%s' % clone_id,
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


def test_openapi_clone_bi_pack(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    pack_id = "default"
    response = wsgi_app.get(base + '/objects/bi_pack/%s' % pack_id, status=200)
    pack = json.loads(response.text)

    clone_id = "cloned_pack"
    new_data = {key: pack["extensions"][key] for key in ["title", "contact_groups", "public"]}
    new_data["title"] = "Test title"

    # Check invalid POST request on existing id
    wsgi_app.post(base + '/objects/bi_pack/%s' % pack_id,
                  content_type='application/json',
                  params=json.dumps(new_data),
                  status=404)

    # Check valid PUT request on existing id
    wsgi_app.put(base + '/objects/bi_pack/%s' % pack_id,
                 content_type='application/json',
                 params=json.dumps(new_data),
                 status=200)

    # Verify that rules/aggregations remain unchanged
    response = wsgi_app.get(base + '/objects/bi_pack/%s' % pack_id, status=200)
    pack = json.loads(response.text)
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1
    assert pack["title"] == "Test title"

    # Check invalid PUT request on new id
    wsgi_app.put(base + '/objects/bi_pack/%s' % clone_id,
                 content_type='application/json',
                 params=json.dumps(new_data),
                 status=404)

    # Save config under different id
    wsgi_app.post(base + '/objects/bi_pack/%s' % clone_id,
                  content_type='application/json',
                  params=json.dumps(new_data),
                  status=200)

    # Verify cloned_pack configuration
    response = wsgi_app.get(base + '/objects/bi_pack/%s' % clone_id, status=200)
    cloned_pack = json.loads(response.text)
    assert cloned_pack["id"] == clone_id

    # Verify that rules/aggregations have been migrated
    assert len(cloned_pack["members"]["rules"]["value"]) == 0
    assert len(cloned_pack["members"]["aggregations"]["value"]) == 0
    assert cloned_pack["title"] == "Test title"


def test_openapi_delete_pack(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    pack_data = {
        "title": "Test pack",
        "contact_groups": [],
        "public": True,
    }

    # Check invalid POST request on existing id
    wsgi_app.post(base + '/objects/bi_pack/test_pack',
                  content_type='application/json',
                  params=json.dumps(pack_data),
                  status=200)

    # Verify creation
    response = wsgi_app.get(base + '/objects/bi_pack/test_pack', status=200)
    pack = json.loads(response.text)
    assert pack["title"] == "Test pack"

    # Delete pack
    wsgi_app.delete(base + '/objects/bi_pack/test_pack', status=204)

    # Verify deletion
    wsgi_app.get(base + '/objects/bi_pack/test_pack', status=404)


def test_openapi_delete_pack_forbidden(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    # Check invalid POST request on existing id
    wsgi_app.delete(base + '/objects/bi_pack/default', content_type='application/json', status=404)


def test_get_non_existing_aggregation(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'
    postfix = '/objects/bi_aggregation/'
    url = f'{base}{postfix}NO_I_DONT_EXIST'

    with pytest.raises(MKGeneralException):
        _response = wsgi_app.get(url=url)
