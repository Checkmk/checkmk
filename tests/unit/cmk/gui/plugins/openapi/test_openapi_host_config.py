#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

from cmk.gui.type_defs import CustomAttr
from cmk.gui.watolib.custom_attributes import save_custom_attrs_to_mk_file
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.utils import version

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


def test_openapi_cluster_host(wsgi_app, with_automation_user, suppress_automation_calls, with_host):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json; charset=utf-8',
    )

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/clusters",
        params='{"host_name": "bazfoo", "folder": "/", "nodes": ["foobar"]}',
        status=200,
        content_type='application/json; charset="utf-8"',
    )

    wsgi_app.call_method(
        'get',
        base + "/objects/host_config/bazfoozle",
        status=404,
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/bazfoo",
        status=200,
    )

    wsgi_app.call_method(
        'put',
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["not_existing"]}',
        status=400,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    wsgi_app.call_method(
        'put',
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["example.com", "bazfoo"]}',
        status=400,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    wsgi_app.call_method(
        'put',
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["example.com"]}',
        status=200,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/bazfoo",
        status=200,
    )
    assert resp.json['extensions']['cluster_nodes'] == ['example.com']


def test_openapi_hosts(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )
    assert isinstance(resp.json['extensions']['attributes']['meta_data']['created_at'], str)
    assert isinstance(resp.json['extensions']['attributes']['meta_data']['updated_at'], str)

    resp = wsgi_app.follow_link(
        resp,
        'self',
        status=200,
    )

    attributes = {
        "ipaddress": "127.0.0.1",
        "snmp_community": {
            "type": "v1_v2_community",
            "community": "blah",
        },
    }
    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        status=200,
        params=json.dumps({'attributes': attributes}),
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
    got_attributes = resp.json['extensions']['attributes']
    assert list(attributes.items()) <= list(got_attributes.items())

    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        status=200,
        params='{"update_attributes": {"alias": "bar"}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
    assert resp.json['extensions']['attributes']['alias'] == "bar"

    resp = wsgi_app.follow_link(
        resp,
        '.../update',
        status=200,
        params='{"remove_attributes": ["alias"]}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
    assert 'alias' not in resp.json['extensions']['attributes']

    # make sure changes are written to disk:
    resp = wsgi_app.follow_link(resp, 'self', status=200)
    assert "alias" not in resp.json['extensions']['attributes']

    # also try to update with wrong attribute
    wsgi_app.follow_link(
        resp,
        '.../update',
        status=400,
        params='{"attributes": {"foobaz": "bar"}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    wsgi_app.follow_link(
        resp,
        '.../delete',
        status=204,
        content_type='application/json',
    )


def test_openapi_host_update_after_move(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    with_host,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "bar", "parent": "/"}',
        status=200,
        content_type='application/json',
    )

    heute = wsgi_app.call_method(
        'get',
        "/NO_SITE/check_mk/api/1.0/objects/host_config/heute",
    )

    _moved_heute = wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/1.0/objects/host_config/heute/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={'If-Match': heute.headers['ETag']},
        content_type='application/json',
        status=200,
    )

    example = wsgi_app.call_method(
        'get',
        "/NO_SITE/check_mk/api/1.0/objects/host_config/example.com",
    )

    moved_example = wsgi_app.call_method(
        'post',
        "/NO_SITE/check_mk/api/1.0/objects/host_config/example.com/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={'If-Match': example.headers['ETag']},
        content_type='application/json',
        status=200,
    )

    moved_example_updated = wsgi_app.follow_link(
        moved_example,
        '.../update',
        status=200,
        params=json.dumps({'attributes': {
            "alias": "foo"
        }}),
        headers={'If-Match': moved_example.headers['ETag']},
        content_type='application/json',
    )

    wsgi_app.follow_link(
        moved_example_updated,
        '.../update',
        status=200,
        params=json.dumps({'attributes': {
            "alias": "foo"
        }}),
        headers={'If-Match': moved_example_updated.headers['ETag']},
        content_type='application/json',
    )


def test_openapi_bulk_hosts(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps({
            "entries": [
                {
                    "host_name": "foobar",
                    "folder": "/",
                    "attributes": {
                        "ipaddress": "127.0.0.2"
                    }
                },
                {
                    "host_name": "sample",
                    "folder": "/",
                    "attributes": {
                        "ipaddress": "127.0.0.2",
                        "site": "NO_SITE",
                    }
                },
            ]
        }),
        status=200,
        content_type='application/json',
    )
    assert len(resp.json['value']) == 2

    _resp = wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            "entries": [{
                "host_name": "foobar",
                "attributes": {
                    "ipaddress": "192.168.1.1",
                    "tag_address_family": "ip-v4-only",
                },
            }],
        }),
        status=200,
        content_type='application/json',
    )

    # verify attribute ipaddress is set corretly
    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )
    assert resp.json['extensions']['attributes']['ipaddress'] == "192.168.1.1"

    # remove attribute ipaddress via bulk request
    wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            "entries": [{
                "host_name": "foobar",
                "remove_attributes": ['ipaddress']
            }],
        }),
        status=200,
        content_type='application/json',
    )

    # verify attribute ipaddress was removed correctly
    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )
    assert 'ipaddress' not in resp.json['extensions']['attributes']

    # adding invalid attribute should fail
    _resp = wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            "entries": [{
                "host_name": "foobar",
                "attributes": {
                    "foobaz": "bar"
                }
            }],
        }),
        status=400,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method('post',
                                 base + "/domain-types/host_config/actions/bulk-delete/invoke",
                                 params=json.dumps({"entries": ["foobar", "sample"]}),
                                 status=204,
                                 content_type='application/json')


def test_openapi_bulk_simple(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps(
            {'entries': [{
                'host_name': 'example.com',
                'folder': '/',
                'attributes': {}
            }]}),
        status=200,
        content_type='application/json',
    )


def test_openapi_bulk_management_protocol(wsgi_app, with_automation_user,
                                          suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    # create example.com test host
    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params=
        '{"host_name": "example.com", "folder": "/", "attributes": {"management_protocol": "none"}}',
        status=200,
        content_type='application/json; charset=utf-8',
    )

    # read management_protocol
    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/example.com",
        status=200,
    )
    assert resp.json['extensions']['attributes']['management_protocol'] == 'none'

    # make sure a value that is not defined in the enum raises an error
    wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({'entries': [{
            'host_name': 'example.com',
            'update_attributes': 'asd',
        }]}),
        status=400,
        content_type='application/json',
    )

    # change management protocol
    wsgi_app.call_method(
        'put',
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            'entries': [{
                'host_name': 'example.com',
                'update_attributes': {
                    "management_protocol": "snmp"
                },
            }]
        }),
        status=200,
        content_type='application/json',
    )

    # make sure it's actually changed
    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/example.com",
        status=200,
    )
    assert resp.json['extensions']['attributes']['management_protocol'] == "snmp"


@pytest.fixture(name="custom_host_attribute")
def _custom_host_attribute():
    try:
        attr: CustomAttr = {
            'name': 'foo',
            'title': 'bar',
            'help': 'foo',
            'topic': 'topic',
            'type': 'TextAscii',
            'add_custom_macro': False,
            'show_in_table': False,
        }
        save_custom_attrs_to_mk_file({'host': [attr]})
        yield
    finally:
        save_custom_attrs_to_mk_file({})


def test_openapi_host_created_timestamp(wsgi_app, with_automation_user) -> None:

    base = '/NO_SITE/check_mk/api/1.0'

    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    json_data = {
        "folder": "/",
        "host_name": "foobar.com",
        "attributes": {
            "ipaddress": "192.168.0.123",
        },
    }

    resp_post = wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )

    created_at_post = resp_post.json["extensions"]["attributes"]["meta_data"]["created_at"]

    resp_get = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar.com",
        status=200,
        headers={"Accept": "application/json"},
    )

    created_at_get = resp_get.json["extensions"]["attributes"]["meta_data"]["created_at"]

    resp_put = wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar.com",
        status=200,
        params='{"attributes": {"ipaddress": "192.168.0.124"}}',
        content_type="application/json",
        headers={
            "If-Match": resp_get.headers["ETag"],
            "Accept": "application/json"
        },
    )

    created_at_put = resp_put.json["extensions"]["attributes"]["meta_data"]["created_at"]
    assert created_at_post == created_at_get == created_at_put


def test_openapi_host_custom_attributes(
    wsgi_app,
    with_automation_user,
    with_host,
    custom_host_attribute,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    # Known custom attribute

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/example.com",
        status=200,
    )

    update1 = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/example.com",
        status=200,
        params='{"attributes": {"foo": "bar"}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    # Internal, non-editable attributes shall not be settable.
    wsgi_app.call_method(
        "put",
        base + "/objects/host_config/example.com",
        status=400,
        params='{"attributes": {"meta_data": "bar"}}',
        headers={
            "If-Match": update1.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
    )

    # Unknown custom attribute

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/example.com",
        status=200,
    )

    wsgi_app.call_method(
        'put',
        base + "/objects/host_config/example.com",
        status=400,
        params='{"attributes": {"foo2": "bar"}}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )


def test_openapi_host_collection(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    with_host,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'get',
        base + "/domain-types/host_config/collections/all",
        status=200,
    )
    for host in resp.json['value']:
        # Check that all entries are domain objects
        assert 'extensions' in host
        assert 'links' in host
        assert 'members' in host
        assert 'title' in host
        assert 'id' in host


def test_openapi_host_rename(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=200,
    )

    _resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobaz",
        status=200,
    )


def test_openapi_host_rename_error_on_not_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/fooba/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=404,
    )


def test_openapi_host_rename_on_invalid_hostname(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobar"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=400,
    )


def test_openapi_host_rename_with_pending_activate_changes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type='application/json',
        headers={'If-Match': resp.headers['ETag']},
        status=409,
    )


def test_openapi_host_move(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    wsgi_app.call_method(
        'post',
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type='application/json',
        status=200,
    )

    _resp = wsgi_app.call_method(
        'post',
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
        status=200,
    )


def test_openapi_host_move_to_non_valid_folder(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    wsgi_app.call_method(
        'post',
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type='application/json',
        status=200,
    )

    wsgi_app.call_method(
        'post',
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/"}',
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
        status=400,
    )


def test_openapi_host_move_of_non_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    _resp = wsgi_app.call_method(
        'post',
        base + "/objects/host_config/foobaz/actions/move/invoke",
        params='{"target_folder": "/"}',
        content_type='application/json',
        status=404,
    )


def test_openapi_host_update_invalid(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "example.com", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    wsgi_app.follow_link(
        resp,
        '.../update',
        status=400,
        params=json.dumps({
            'attributes': {
                'ipaddress': '192.168.0.123'
            },
            'update_attributes': {
                'ipaddress': '192.168.0.123'
            },
            'remove_attributes': ['tag_foobar']
        }),
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )


def test_openapi_create_host_with_contact_group(
    wsgi_app,
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    group = {'name': "code_monkeys", 'alias': "banana team", 'customer': 'global'}
    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/contact_group_config/collections/all",
        params=json.dumps(group),
        status=200,
        content_type='application/json',
    )

    json_data = {
        'folder': '/',
        'host_name': 'example.com',
        'attributes': {
            'ipaddress': '192.168.0.123',
            'contactgroups': {
                'groups': ["code_monkeys"],
                'use': False,
                'use_for_services': False,
                'recurse_use': False,
                'recurse_perms': False
            },
        },
    }
    wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type='application/json',
    )


@managedtest
def test_openapi_create_host_with_custom_attributes(
    wsgi_app,
    with_automation_user,
    custom_host_attribute,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "ipaddress": "192.168.0.123",
            "foo": "abc",
        },
    }
    resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
    assert "ipaddress" in resp.json["extensions"]["attributes"]
    assert "foo" in resp.json["extensions"]["attributes"]


def test_openapi_add_host_with_attributes(
    wsgi_app,
    with_automation_user,
) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    response = wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps({
            "host_name": "foobar",
            "folder": "/",
            "attributes": {
                "alias": "ALIAS",
                "locked_by": {
                    "site_id": "site_id",
                    "program_id": "dcd",
                    "instance_id": "connection_id",
                },
                "locked_attributes": ["alias"],
            },
        }),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )

    api_attributes = response.json["extensions"]["attributes"]
    assert api_attributes["alias"] == "ALIAS"
    assert api_attributes["locked_by"] == {
        "instance_id": "connection_id",
        "program_id": "dcd",
        "site_id": "site_id",
    }
    assert api_attributes["locked_attributes"] == ["alias"]

    # Ensure that the attributes were stored as expected
    hosts_config = Folder.root_folder()._load_hosts_file()
    assert hosts_config is not None
    assert hosts_config["host_attributes"]["foobar"]["locked_attributes"] == ["alias"]
    assert hosts_config["host_attributes"]["foobar"]["locked_by"] == (
        "site_id",
        "dcd",
        "connection_id",
    )


def test_openapi_bulk_add_hosts_with_attributes(
    wsgi_app,
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    response = wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps({
            "entries": [
                {
                    "host_name": "ding",
                    "folder": "/",
                    "attributes": {
                        "ipaddress": "127.0.0.2"
                    },
                },
                {
                    "host_name": "dong",
                    "folder": "/",
                    "attributes": {
                        "ipaddress": "127.0.0.2",
                        "site": "NO_SITE",
                    },
                },
            ]
        }),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    assert len(response.json["value"]) == 2

    response = wsgi_app.call_method(
        "put",
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps({
            "entries": [{
                "host_name": "ding",
                "update_attributes": {
                    "locked_by": {
                        "site_id": "site_id",
                        "program_id": "dcd",
                        "instance_id": "connection_id",
                    },
                    "locked_attributes": ["alias"],
                },
            }],
        }),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # verify attribute ipaddress is set corretly
    response = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/ding",
        status=200,
        headers={"Accept": "application/json"},
    )

    api_attributes = response.json["extensions"]["attributes"]
    assert api_attributes["locked_by"] == {
        "instance_id": "connection_id",
        "program_id": "dcd",
        "site_id": "site_id",
    }
    assert api_attributes["locked_attributes"] == ["alias"]


def test_openapi_host_with_invalid_labels(
    wsgi_app,
    with_automation_user,
) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'
    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "labels": {
                "label": ["invalid_label_entry", "another_one"]
            }
        },
    }
    wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=400,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


def test_openapi_host_with_labels(wsgi_app, with_automation_user) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'
    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "labels": {
                "label": "value",
            }
        },
    }
    resp = wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["attributes"]["labels"] == {"label": "value"}
