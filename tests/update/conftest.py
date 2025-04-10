#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
def pytest_addoption(parser):
    parser.addoption(
        "--disable-interactive-mode",
        action="store_true",
        default=False,
        help="Disable interactive site creation and update. Use CLI instead.",
    )
    parser.addoption(
        "--latest-base-version",
        action="store_true",
        default=False,
        help="Use the latest base-version only.",
    )
    parser.addoption(
        "--store-lost-services",
        action="store_true",
        default=False,
        help="Store list of lost services in a json reference.",
    )
    parser.addoption(
        "--disable-rules-injection",
        action="store_true",
        default=False,
        help="Disable rules' injection in the test-site.",
    )
    parser.addoption(
        "--target-edition",
        action="store",
        default=None,
        help="Edition for the target test-site; Options: CRE, CEE, CCE, CSE, CME.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "cee: marks tests using an enterprise-edition site")
    config.addinivalue_line("markers", "cce: marks tests using a cloud-edition site")
    config.addinivalue_line("markers", "cse: marks tests using a saas-edition site")
    config.addinivalue_line("markers", "cme: marks tests using a managed-edition site")
