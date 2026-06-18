#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for clearing inherited host labels via the LABEL_CLEAR_VALUE sentinel.

A child folder or host can override a label set by a parent folder back to
"off". The attribute returns LABEL_CLEAR_VALUE for the key; the value survives
the add-only inheritance merge and is stripped by Host.labels(), so consumers
see the key as absent.
"""

# mypy: disable-error-code="typeddict-unknown-key"

import os
import shutil
from collections.abc import Iterator
from typing import Any

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.fields import String
from cmk.gui.fields import Field
from cmk.gui.valuespec import TextInput, ValueSpec
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeValueSpec,
    host_attribute_registry,
    HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS,
    HostAttributeTopic,
    LABEL_CLEAR_VALUE,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.utils.labels import Labels


@pytest.mark.usefixtures("clearing_attribute")
def test_child_clears_inherited_label() -> None:
    """A subfolder set to "off" removes the relay label inherited from its parent."""
    root = folder_tree().root_folder()
    parent = root.create_subfolder(
        "parent",
        "parent",
        {"clearing_test": "relay1"},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    sub = parent.create_subfolder(
        "sub",
        "sub",
        {"clearing_test": ""},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    sub.create_hosts(
        [(HostName("host-1"), {}, [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    host = sub.host(HostName("host-1"))
    assert host is not None
    labels = host.labels()
    assert "test/relay" not in labels
    assert "test/relay_monitored" not in labels


@pytest.mark.usefixtures("clearing_attribute")
def test_grandchild_reenables_after_clear() -> None:
    """A deeper folder can re-enable the label after an intermediate folder cleared it."""
    root = folder_tree().root_folder()
    parent = root.create_subfolder(
        "parent",
        "parent",
        {"clearing_test": "relay1"},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    sub = parent.create_subfolder(
        "sub",
        "sub",
        {"clearing_test": ""},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    grandsub = sub.create_subfolder(
        "grandsub",
        "grandsub",
        {"clearing_test": "relay2"},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    grandsub.create_hosts(
        [(HostName("host-2"), {}, [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    host = grandsub.host(HostName("host-2"))
    assert host is not None
    labels = host.labels()
    assert labels["test/relay"] == "relay2"
    assert labels["test/relay_monitored"] == "yes"


@pytest.mark.usefixtures("clearing_attribute")
def test_inherited_relay_label_without_override() -> None:
    """A host with no override inherits the parent folder's relay label unchanged."""
    root = folder_tree().root_folder()
    parent = root.create_subfolder(
        "parent",
        "parent",
        {"clearing_test": "relay1"},
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    parent.create_hosts(
        [(HostName("host-3"), {}, [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )
    host = parent.host(HostName("host-3"))
    assert host is not None
    labels = host.labels()
    assert labels["test/relay"] == "relay1"


class _ClearingTestAttribute(ABCHostAttributeValueSpec):
    """Mimics the relay attribute: emits a label for a real value, and the
    clear-sentinel for an empty (explicit "off") value."""

    def name(self) -> str:
        return "clearing_test"

    def title(self) -> str:
        return "Clearing test"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS

    def openapi_field(self) -> Field:
        return String()

    def valuespec(self) -> ValueSpec[Any]:
        return TextInput()

    def labels(self, value: Any) -> Labels:
        if value:
            return {"test/relay": value, "test/relay_monitored": "yes"}
        return {"test/relay": LABEL_CLEAR_VALUE, "test/relay_monitored": LABEL_CLEAR_VALUE}


@pytest.fixture(autouse=True)
def test_env(with_admin_login: UserId, load_config: None) -> Iterator[None]:
    # Provide an application context and start from clean folder/host caches.
    tree = folder_tree()
    tree.invalidate_caches()

    yield

    # Remove WATO folders created by the test.
    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


@pytest.fixture(name="clearing_attribute")
def _clearing_attribute() -> Iterator[None]:
    host_attribute_registry.register(_ClearingTestAttribute)
    try:
        yield
    finally:
        host_attribute_registry.unregister("clearing_test")


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(make_audit_log_change_hook(use_git=False),),
    )
