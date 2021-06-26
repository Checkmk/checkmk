#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import pytest

from cmk.utils import store
from cmk.utils.type_defs import CheckPluginName
from cmk.base.api.agent_based.value_store._utils import (
    _DynamicValueStore,
    _EffectiveValueStore,
    _StaticValueStore,
    _ValueStore,
    ValueStoreManager,
)

_TEST_KEY = ("check", "item", "user-key")


class Test_DynamicValueStore:
    @staticmethod
    def test_init():
        dad = _DynamicValueStore()
        assert not dad
        assert not dad.removed_keys

    @staticmethod
    def test_removed_del():
        dad = _DynamicValueStore()
        try:
            del dad[_TEST_KEY]
        except KeyError:
            pass
        assert dad.removed_keys == {_TEST_KEY}

    @staticmethod
    def test_removed_pop():
        dad = _DynamicValueStore()
        dad.pop(_TEST_KEY, None)
        assert dad.removed_keys == {_TEST_KEY}

    @staticmethod
    def test_setitem():
        dad = _DynamicValueStore()
        value = object()
        dad[_TEST_KEY] = value
        assert dad[_TEST_KEY] is value
        assert not dad.removed_keys

        # remove and re-add (no, this is not trivial!)
        dad.pop(_TEST_KEY)
        dad[_TEST_KEY] = value
        assert not dad.removed_keys

    @staticmethod
    def test_delitem():
        dad = _DynamicValueStore()
        dad[_TEST_KEY] = None
        assert _TEST_KEY in dad  # setup

        del dad[_TEST_KEY]
        assert _TEST_KEY not in dad

    @staticmethod
    def test_popitem():
        dad = _DynamicValueStore()
        dad[_TEST_KEY] = None
        assert _TEST_KEY in dad  # setup

        dad.pop(_TEST_KEY)
        assert _TEST_KEY not in dad


class Test_StaticValueStore:
    def _mock_load(self, mocker):
        stored_item_states = {
            (
                "check1",
                None,
                "stored-user-key-1",
            ): 23,
            (
                "check2",
                "item",
                "stored-user-key-2",
            ): 42,
        }

        mocker.patch.object(
            store,
            "load_object_from_file",
            side_effect=lambda *a, **kw: stored_item_states,
        )

    def _mock_store(self, mocker):
        mocker.patch.object(
            store,
            "save_object_to_file",
            autospec=True,
        )

    def test_mapping_features(self, mocker):

        self._mock_load(mocker)
        svs = _StaticValueStore("test-host", lambda msg: None)
        assert svs.get(("check_no", None, "moo")) is None
        with pytest.raises(KeyError):
            _ = svs[("check_no", None, "moo")]
        assert len(svs) == 2

        assert svs.get(("check1", None, "stored-user-key-1")) == 23
        assert svs[("check2", "item", "stored-user-key-2")] == 42
        assert list(svs) == [
            ("check1", None, "stored-user-key-1"),
            ("check2", "item", "stored-user-key-2"),
        ]
        assert len(svs) == 2

    def test_store(self, mocker):

        self._mock_load(mocker)
        self._mock_store(mocker)

        svs = _StaticValueStore("test-host", lambda msg: None)

        svs.disksync(
            removed={("check2", "item", "stored-user-key-2")},
            updated=[(("check3", "el Barto", "Ay caramba"), "ASDF")],
        )

        expected_values = {
            ("check1", None, "stored-user-key-1"): 23,
            ("check3", "el Barto", "Ay caramba"): "ASDF",
        }
        written = store.save_object_to_file.call_args.args[1]  # type: ignore[attr-defined]
        assert written == expected_values
        assert list(svs.items()) == list(expected_values.items())


class Test_EffectiveValueStore:
    @staticmethod
    def _get_store() -> _EffectiveValueStore:
        dynstore = _DynamicValueStore()
        dynstore.update({
            ("dyn", "key", "1"): "dyn-val-1",
            ("dyn", "key", "2"): "dyn-val-2",
        })
        return _EffectiveValueStore(
            dynamic=dynstore,
            static=
            {  # type: ignore[arg-type]
                ("stat", "key", "1"): "stat-val-1",
                ("stat", "key", "2"): "stat-val-2",
            },
        )

    def test_getitem(self):
        evs = self._get_store()
        assert evs[("stat", "key", "1")] == "stat-val-1"
        assert evs.get(("stat", "key", "2")) == "stat-val-2"
        assert evs.get(("stat", "key", "3")) is None
        assert evs[("dyn", "key", "1")] == "dyn-val-1"
        assert evs.get(("dyn", "key", "2")) == "dyn-val-2"
        assert evs.get(("dyn", "key", "3")) is None

    def test_delitem(self):
        evs = self._get_store()
        assert ("stat", "key", "1") in evs
        assert ("dyn", "key", "2") in evs

        del evs[("stat", "key", "1")]
        assert ("stat", "key", "1") not in evs

        with pytest.raises(KeyError):
            del evs[("stat", "key", "1")]

        del evs[("dyn", "key", "1")]
        assert ("dyn", "key", "1") not in evs

    def test_pop(self):
        evs = self._get_store()
        assert ("stat", "key", "1") in evs
        assert ("dyn", "key", "2") in evs

        evs.pop(("stat", "key", "1"))
        assert ("stat", "key", "1") not in evs

        evs.pop(("dyn", "key", "1"))
        assert ("dyn", "key", "1") not in evs

    def test_iter(self):
        evs = self._get_store()
        assert sorted(evs) == [("dyn", "key", "1"), ("dyn", "key", "2"), ("stat", "key", "1"),
                               ("stat", "key", "2")]

        evs.pop(("stat", "key", "1"))
        assert sorted(evs) == [("dyn", "key", "1"), ("dyn", "key", "2"), ("stat", "key", "2")]

        evs.pop(("dyn", "key", "2"))
        assert sorted(evs) == [("dyn", "key", "1"), ("stat", "key", "2")]


class Test_ValueStore:
    @staticmethod
    def _get_store() -> _ValueStore:
        return _ValueStore(
            data={
                ("check1", "item", "key1"): 42,
                ("check2", "item", "key2"): 23,
            },
            service_id=(CheckPluginName("check1"), "item"),
        )

    def test_separation(self):
        s_store = self._get_store()
        assert "key1" in s_store
        assert "key2" not in s_store

    def test_invalid_key(self):
        s_store = self._get_store()
        with pytest.raises(TypeError):
            s_store[2] = "key must be string!"  # type: ignore[index]


class TestValueStoreManager:
    @staticmethod
    def test_namespace_context():
        vsm = ValueStoreManager("test-host")
        service_inner = (CheckPluginName("unit_test_inner"), None)
        service_outer = (CheckPluginName("unit_test_outer"), None)

        assert vsm.active_service_interface is None

        with vsm.namespace(service_outer):
            assert vsm.active_service_interface is not None
            vsm.active_service_interface["key"] = "outer"

            with vsm.namespace(service_inner):
                assert vsm.active_service_interface is not None
                assert "key" not in vsm.active_service_interface
                vsm.active_service_interface["key"] = "inner"

            assert vsm.active_service_interface["key"] == "outer"

        assert vsm.active_service_interface is None
