#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Data flow of agent_kube:

Python code wise the lowest level is the kubernetes.client. This client is used
to query the kubernetes cluster via the kubernetes API. The returned objects
are python objects that were automatically generated with the help the
openapi doc that defines the kuberentes API and are part of the kubernetes
python library.

If the API changes, and we update the kubernetes python library the python
objects will chagne. In order to make this changes more easy we added
.schemata.api which defines our own objects that should be stable between
kubernetes versions. The idea is that we only have to adapt the layer between
kubernetes.client and .schemata.api when kubernetes changes data structures.

The wrapper around the kubernetes library is api_server.APIServer

The function used to transform from kubernetes specific objects to our own data
structures life in .transform

The data gathered needs be transported to the checkmk server. The common
checkmk mechanism to do this is to create a agent section and parse this
section in the check. We use pydantic for serializing and deserializing this
data. The schemata used for serializing live mostly in .schemata.section, the
schemata used for deserializing in cmk.base.plugins.agent_based.utils.k8s
We use a unit test to make sure they stay in sync.

So the layering normally looks like that::
    kubernetes python lib -> api_server --[api-layer]--> agent_kube --[section-layer]--> section

But to make development a bit easier it's also possible to skip the section-layer::
    kubernetes python lib -> api_server --[api-layer]--> agent_kube -------------------> section

This way you don't have to reinitialize the data structure only to full fill the layering.

"""
