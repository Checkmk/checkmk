#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.bi.bi_node_generator import BINodeGenerator
from cmk.utils.bi.bi_searcher import bi_searcher
from cmk.utils.bi.bi_rule import BIRule
from cmk.utils.bi.bi_rule_interface import bi_rule_id_registry
from cmk.utils.bi.bi_data_fetcher import bi_structure_fetcher, bi_status_fetcher
from cmk.utils.bi.bi_packs import bi_packs

import bi_test_data.sample_config as sample_config


@pytest.fixture(scope="function")
def use_test_structure_data():
    try:
        bi_structure_fetcher.add_site_data("heute", sample_config.bi_structure_states)
        bi_searcher.set_hosts(bi_structure_fetcher.hosts)
        yield
    finally:
        bi_searcher.cleanup()
        bi_structure_fetcher.cleanup()


@pytest.fixture(scope="function")
def use_test_status_data():
    try:
        bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(
            sample_config.bi_status_rows)
        yield bi_status_fetcher
    finally:
        bi_status_fetcher.cleanup()


@pytest.fixture(scope="function")
def use_test_acknowledgement_status_data():
    try:
        bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(
            sample_config.bi_acknowledgment_status_rows)
        yield bi_status_fetcher
    finally:
        bi_status_fetcher.cleanup()


@pytest.fixture(scope="function")
def use_test_downtime_status_data():
    try:
        bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(
            sample_config.bi_downtime_status_rows)
        yield bi_status_fetcher
    finally:
        bi_status_fetcher.cleanup()


@pytest.fixture(scope="function")
def use_test_service_period_status_data():
    try:
        bi_status_fetcher.states = bi_status_fetcher.create_bi_status_data(
            sample_config.bi_service_period_status_rows)
        yield bi_status_fetcher
    finally:
        bi_status_fetcher.cleanup()


@pytest.fixture(scope="function")
def dummy_bi_rule():
    rule_id = "dummy_rule"
    try:
        node_schema = BINodeGenerator.schema()().dump({}).data
        node_schema["action"]["host_regex"] = "heute_clone"
        schema_config = BIRule.schema()().dump({"id": rule_id}).data
        schema_config["nodes"].append(node_schema)
        yield BIRule(schema_config)
    finally:
        bi_rule_id_registry.unregister(rule_id)


@pytest.fixture(scope="function")
def bi_packs_sample_config(monkeypatch):
    try:
        bi_packs.load_config_from_schema(sample_config.bi_packs_config)
        monkeypatch.setattr("cmk.utils.bi.bi_packs.bi_packs.load_config", lambda: None)
        monkeypatch.setattr("cmk.utils.bi.bi_packs.bi_packs.save_config", lambda: None)
        yield bi_packs
    finally:
        bi_packs.cleanup()
