#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import parse_namespace_metadata


class TestAPINamespace:
    def test_parse_metadata(self, core_client, dummy_host):
        namespace_metadata = {
            "items": [
                {
                    "metadata": {
                        "name": "checkmk-monitoring",
                        "uid": "753292ba-5e0e-4267-a0f1-77a3c6b4d55e",
                        "resourceVersion": "509",
                        "creationTimestamp": "2022-03-25T13:24:42Z",
                        "labels": {"kubernetes.io/metadata.name": "checkmk-monitoring"},
                        "annotations": {
                            "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"v1","kind":"Namespace","metadata":{"annotations":{},"name":"checkmk-monitoring"}}\n'
                        },
                    },
                },
            ],
        }

        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/api/v1/namespaces",
            body=json.dumps(namespace_metadata),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            namespace = list(core_client.list_namespace().items)[0]
        metadata = parse_namespace_metadata(namespace.metadata)
        assert isinstance(metadata, api.NamespaceMetaData)
        assert metadata.name == "checkmk-monitoring"
        assert isinstance(metadata.creation_timestamp, float)
        assert metadata.labels == {
            "kubernetes.io/metadata.name": api.Label(
                name="kubernetes.io/metadata.name", value="checkmk-monitoring"
            )
        }
