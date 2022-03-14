#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Cisco Prime API response parser
# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
see https://solutionpartner.cisco.com/media/prime-infrastructure-api-reference-v3-0/192.168.115.187/webacs/api/v1/data/ClientCountscc3b.html
"""

import json


def parse_cisco_prime(key, info):
    """Parse JSON and return queryResponse/entity entry (a list of dicts)
    The JSON outputs of agent_cisco_prime provides the following structure:

    {
      "queryResponse": {
        "entity": [
          {
            <key>: {
              "@id": str,
              ... data items ..
            },
            ... (other values not of our interest)
          },
          ...
        ],
        ... (other values not of our interest)
      }
    }
    """
    elements = json.loads(info[0][0])["queryResponse"]["entity"]
    return {item["@id"]: item for elem in elements for item in (elem[key],)}
