#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
=============================
Agent based API ("Check API")
=============================

This API provides tools for the implementation of

 * **section definitions** parsing the raw data and discovering host labels

 * **check plugins** subscribing to sections and creating services

 * **inventory plugins** subscribing to sections and creating entries for the HW/SW inventory

Version 1
=========

.. toctree::

   cmk.base.plugins.agent_based.agent_based_api.v1
   cmk.base.plugins.agent_based.agent_based_api.v1.clusterize
   cmk.base.plugins.agent_based.agent_based_api.v1.register
   cmk.base.plugins.agent_based.agent_based_api.v1.render
   cmk.base.plugins.agent_based.agent_based_api.v1.type_defs
"""
