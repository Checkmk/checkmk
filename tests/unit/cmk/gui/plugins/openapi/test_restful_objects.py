#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.restful_objects import response_schemas


def test_host_collection():
    errors = response_schemas.HostCollection().validate({
        'id': 'host',
        'domainType': 'host_config',
        'value': [{
            'rel': 'urn:org.restfulobjects:rels/value;collection="all"',
            'href': '/objects/host_config/foobar',
            'method': 'GET',
            'type': 'application/json;profile="urn:org.restfulobjects:rels/object"',
            'domainType': 'link',
            'title': 'foobar'
        }, {
            'rel': 'urn:org.restfulobjects:rels/value;collection="all"',
            'href': '/objects/host_config/sample',
            'method': 'GET',
            'type': 'application/json;profile="urn:org.restfulobjects:rels/object"',
            'domainType': 'link',
            'title': 'sample'
        }],
        'links': [{
            'rel': 'self',
            'href': '/domain-types/host_config/collections/all',
            'method': 'GET',
            'type': 'application/json',
            'domainType': 'link'
        }]
    })
    if errors:
        raise Exception(errors)


def test_domain_object():
    errors = response_schemas.DomainObject().validate({
        'domainType': 'folder',
        'extensions': {
            'attributes': {
                'meta_data': {
                    'created_at': 1583248090.277515,
                    'created_by': u'test123-jinlc',
                    'update_at': 1583248090.277516,
                    'updated_at': 1583248090.324114
                }
            }
        },
        'links': [{
            'domainType': 'link',
            'href': '/objects/folder/a71684ebd8fe49548263083a3da332c8',
            'method': 'GET',
            'rel': 'self',
            'type': 'application/json'
        }, {
            'domainType': 'link',
            'href': '/objects/folder/a71684ebd8fe49548263083a3da332c8',
            'method': 'PUT',
            'rel': '.../update',
            'type': 'application/json'
        }, {
            'domainType': 'link',
            'href': '/objects/folder/a71684ebd8fe49548263083a3da332c8',
            'method': 'DELETE',
            'rel': '.../delete',
            'type': 'application/json'
        }],
        'members': {
            'move': {
                'id': 'move',
                'links': [{
                    'domainType': 'link',
                    'href': '/objects/folder/a71684ebd8fe49548263083a3da332c8',
                    'method': 'GET',
                    'rel': 'up',
                    'type': 'application/json'
                }, {
                    'domainType': 'link',
                    'href': '/objects/folder/a71684ebd8fe49548263083a3da332c8/actions/move',
                    'method': 'GET',
                    'rel': '.../details;action="move"',
                    'type': 'application/json'
                }, {
                    'domainType': 'link',
                    'href': '/objects/folder/a71684ebd8fe49548263083a3da332c8/actions/move/invoke',
                    'method': 'POST',
                    'rel': '.../invoke;action="move"',
                    'type': 'application/json'
                }],
                'memberType': 'action'
            }
        },
        'title': u'foobar'
    })

    if errors:
        raise Exception(errors)
