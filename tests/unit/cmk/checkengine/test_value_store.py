#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.checkengine import value_store
from cmk.checkengine.plugins import CheckPluginName, ServiceID

from cmk.agent_based.v1.value_store import get_value_store, set_value_store_manager


def test_load_host_value_store_loads_file(tmp_path: Path) -> None:
    service_id = ServiceID(CheckPluginName("test_service"), None)
    raw_content = '[[["test_load_host_value_store_loads_file", "test_service", null], {"loaded_file": "True"}]]'

    stores_file = tmp_path / "test_host_value_store"

    stores_file.write_text(raw_content)

    with set_value_store_manager(
        value_store.ValueStoreManager(
            HostName("test_load_host_value_store_loads_file"),
            value_store.AllValueStoresStore(
                stores_file,
                log_debug=lambda x: None,
            ),
        ),
        store_changes=False,
    ) as mgr:
        with mgr.namespace(service_id):
            assert get_value_store()["loaded_file"] is True  # trueish is not enough


class TestAllValueStoresStore:
    def _get_avss(self, file: Path) -> value_store.AllValueStoresStore:
        file.write_text(
            "["
            '[["host1", "service1", "item"], {"key": "value1"}],'
            '[["host1", "service2", null], {"key": "value2"}]'
            "]"
        )
        return value_store.AllValueStoresStore(file, log_debug=lambda x: None)

    def test_load_without_file(self, tmp_path: Path) -> None:
        file = tmp_path / "no-file"
        assert not file.exists()
        assert value_store.AllValueStoresStore(file).load() == {}

    def test_load(self, tmp_path: Path) -> None:
        assert self._get_avss(tmp_path / "file").load() == {
            (HostName("host1"), "service1", "item"): {"key": "value1"},
            (HostName("host1"), "service2", None): {"key": "value2"},
        }

    def test_update(self, tmp_path: Path) -> None:
        file = tmp_path / "file"
        avss1 = self._get_avss(file)
        avss2 = self._get_avss(file)

        avss1.update({(HostName("host1"), "service1", "item"): {"key": "new_value1"}})
        avss2.update({(HostName("host1"), "service2", None): {"key": "new_value2"}})

        assert value_store.AllValueStoresStore(file, log_debug=lambda x: None).load() == {
            (HostName("host1"), "service1", "item"): {"key": "new_value1"},
            (HostName("host1"), "service2", None): {"key": "new_value2"},
        }


class _BrokenRepr(str):
    def __repr__(self) -> str:
        raise ValueError("I'm broken!")


class Test_ValueStore:
    @staticmethod
    def _get_vs() -> value_store._ValueStore:
        return value_store._ValueStore(
            {
                "good_key": "'value'",
                "bad_key": "inf",
            }
        )

    def test_getitem_ok(self) -> None:
        vs = self._get_vs()
        assert vs["good_key"] == "value"

    def test_getitem_misses(self) -> None:
        vs = self._get_vs()
        with pytest.raises(KeyError):
            _ = vs["missing_key"]

    def test_getitem_bad(self) -> None:
        vs = self._get_vs()
        with pytest.raises(ValueError):
            _ = vs["bad_key"]

    def test_setitem(self) -> None:
        vs = self._get_vs()
        vs["good_key"] = "new_value"
        assert vs["good_key"] == "new_value"

    def test_setitem_mutable(self) -> None:
        vs = self._get_vs()
        my_dict = vs.setdefault("mutable", {})
        my_dict["foo"] = "bar"  # type: ignore[index]
        assert vs["mutable"]["foo"] == "bar"  # type: ignore[index]

    def test_setitem_bad_key(self) -> None:
        vs = self._get_vs()
        with pytest.raises(TypeError):
            vs[2] = "key must be string!"  # type: ignore[index]

    def test_delitem(self) -> None:
        vs = self._get_vs()
        del vs["good_key"]
        assert "good_key" not in vs

    def test_iter(self) -> None:
        assert list(self._get_vs()) == ["good_key", "bad_key"]

    def test_len(self) -> None:
        assert len(self._get_vs()) == 2

    def test_write_rogue(self) -> None:
        vs = self._get_vs()
        # it's unlikely to encounter an object that can't be repr'd, but we need to deal with it
        rogue = _BrokenRepr()
        vs["rogue"] = rogue
        assert vs["rogue"] is rogue

        # next time we access it, it will raise
        next_times_vs = value_store._ValueStore(vs.export())
        with pytest.raises(SyntaxError):
            _ = next_times_vs["rogue"]


_TEST_HOST = HostName("test-host")
_SERVICE_INNER = ServiceID(CheckPluginName("unit_test_inner"), None)
_SERVICE_OUTER = ServiceID(CheckPluginName("unit_test_outer"), None)
_KEY_INNER = (str(_TEST_HOST), str(_SERVICE_INNER[0]), _SERVICE_INNER[1])
_KEY_OUTER = (str(_TEST_HOST), str(_SERVICE_OUTER[0]), _SERVICE_OUTER[1])


class _AllValueStoresStoreSpy(value_store.AllValueStoresStore):
    def __init__(self) -> None:
        super().__init__(Path(), log_debug=lambda x: None)
        self.inspect_updated: Mapping[value_store.ValueStoreKey, Mapping[str, str]] | None = None

    def load(self) -> Mapping[value_store.ValueStoreKey, Mapping[str, str]]:
        return {}

    def update(self, update: Mapping[value_store.ValueStoreKey, Mapping[str, str]]) -> None:
        self.inspect_updated = update


class TestValueStoreManager:
    @staticmethod
    def test_namespace_context() -> None:
        store = _AllValueStoresStoreSpy()
        vsm = value_store.ValueStoreManager(_TEST_HOST, store)

        assert vsm.active_service_interface is None

        with vsm.namespace(_SERVICE_OUTER):
            assert vsm.active_service_interface is not None
            vsm.active_service_interface["key"] = "outer"

            with vsm.namespace(_SERVICE_INNER):
                assert vsm.active_service_interface is not None
                assert "key" not in vsm.active_service_interface
                vsm.active_service_interface["key"] = "inner"

            assert vsm.active_service_interface["key"] == "outer"

        assert vsm.active_service_interface is None

        vsm.save()

        assert store.inspect_updated == {
            _KEY_OUTER: {"key": "'outer'"},
            _KEY_INNER: {"key": "'inner'"},
        }

    @staticmethod
    def test_skip_empty() -> None:
        store = _AllValueStoresStoreSpy()
        vsm = value_store.ValueStoreManager(_TEST_HOST, store)

        with vsm.namespace(_SERVICE_OUTER):
            pass

        vsm.save()

        assert store.inspect_updated is not None
        assert _KEY_OUTER not in store.inspect_updated
