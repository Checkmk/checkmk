#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import web

def test_global_settings(site, web):
    r = web.get("wato.py")
    assert "Global Settings" in r.text


def test_add_host(web):
    try:
        # Also tests get_host
        web.add_host("test-host", attributes={
            "ipaddress": "127.0.0.1",
        })
    finally:
        web.delete_host("test-host")


def test_get_all_hosts_basic(web):
    try:
        web.add_host("test-host-list", attributes={
            "ipaddress": "127.0.0.1",
        })

        hosts = web.get_all_hosts()
        assert "test-host-list" in hosts
    finally:
        web.delete_host("test-host-list")


def test_delete_host(web):
    try:
        web.add_host("test-host-delete", attributes={
            "ipaddress": "127.0.0.1",
        })
    finally:
        web.delete_host("test-host-delete")


def test_discover_servics(web):
    try:
        web.add_host("test-host-discovery", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.discover_services("test-host-discovery")
    finally:
        web.delete_host("test-host-discovery")


def test_activate_changes(web, site):
    try:
        web.add_host("test-host-activate", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.activate_changes()

        result = site.live.query("GET hosts\nColumns: name\nFilter: name = test-host-activate\n")
        assert result == [["test-host-activate"]]
    finally:
        web.delete_host("test-host-activate")
        web.activate_changes()
