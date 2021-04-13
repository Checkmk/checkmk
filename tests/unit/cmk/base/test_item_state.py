#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import pytest  # type: ignore[import]

from cmk.utils import store
from cmk.utils.exceptions import MKGeneralException
from cmk.base import item_state

_TEST_KEY = ("check", "item", "user-key")


class Test_DynamicValueStore:
    @staticmethod
    def test_init():
        dad = item_state._DynamicValueStore()
        assert not dad
        assert not dad.removed_keys

    @staticmethod
    def test_removed_del():
        dad = item_state._DynamicValueStore()
        try:
            del dad[_TEST_KEY]
        except KeyError:
            pass
        assert dad.removed_keys == {_TEST_KEY}

    @staticmethod
    def test_removed_pop():
        dad = item_state._DynamicValueStore()
        dad.pop(_TEST_KEY, None)
        assert dad.removed_keys == {_TEST_KEY}

    @staticmethod
    def test_setitem():
        dad = item_state._DynamicValueStore()
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
        dad = item_state._DynamicValueStore()
        dad[_TEST_KEY] = None
        assert _TEST_KEY in dad  # setup

        del dad[_TEST_KEY]
        assert _TEST_KEY not in dad

    @staticmethod
    def test_popitem():
        dad = item_state._DynamicValueStore()
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

        svs = item_state._StaticValueStore("test-host", lambda msg: None)
        assert svs.get(("check_no", None, "moo")) is None
        with pytest.raises(KeyError):
            _ = svs[("check_no", None, "moo")]
        assert list(svs) == []
        assert len(svs) == 0

        self._mock_load(mocker)
        svs.load()
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

        svs = item_state._StaticValueStore("test-host", lambda msg: None)
        svs.load()

        svs.store(
            removed={("check2", "item", "stored-user-key-2")},
            updated={("check3", "el Barto", "Ay caramba"): "ASDF"},
        )

        expected_values = {
            ("check1", None, "stored-user-key-1"): 23,
            ("check3", "el Barto", "Ay caramba"): "ASDF",
        }
        written = store.save_object_to_file.call_args.args[1]  # type: ignore[attr-defined]
        assert written == expected_values
        assert list(svs.items()) == list(expected_values.items())


def test_item_state_prefix_required():
    cis = item_state.CachedItemStates()
    # we *must* set a prefix:
    with pytest.raises(MKGeneralException):
        _ = cis.get_item_state("user-key", None)


def test_set_get_item_state_prefix():
    cis = item_state.CachedItemStates()
    test_prefix = ("unit-test", None)
    cis.set_item_state_prefix(test_prefix)
    assert cis.get_item_state_prefix() == test_prefix


def test_no_host_needs_to_be_loaded():
    cis = item_state.CachedItemStates()
    cis.set_item_state_prefix(("unit-test", None))
    # weirdly, this is enough. No need to load any host:
    assert cis.get_item_state("user-key", None) is None


def test_item_state_unloaded():
    # I am not really sure which (if any) part of the following behaviour
    # is desired.
    # This test is only supposed to make the status quo visible.

    test_prefix = ("unit-test", None)
    cis = item_state.CachedItemStates()
    cis.set_item_state_prefix(test_prefix)

    # add some keys:
    cis.set_item_state("one", 1)
    cis.set_item_state("two", 2)
    assert cis.get_item_state("one") == 1
    assert cis.get_all_item_states() == {
        test_prefix + ("one",): 1,
        test_prefix + ("two",): 2,
    }

    cis.clear_item_state("one")
    assert cis.get_item_state("one", None) is None
    assert cis.get_all_item_states() == {
        test_prefix + ("two",): 2,
    }


def test_item_state_loaded(mocker):

    test_prefix = ("unit-test", None)
    stored_item_states = {
        test_prefix + ("stored-user-key-1",): 23,
        test_prefix + ("stored-user-key-2",): 42,
    }

    mocker.patch.object(
        store,
        "load_object_from_file",
        side_effect=lambda *a, **kw: stored_item_states,
    )

    mocker.patch.object(
        store,
        "save_object_to_file",
        autospec=True,
    )

    cis = item_state.CachedItemStates()
    cis.load("hostname")
    cis.set_item_state_prefix(test_prefix)

    assert cis.get_all_item_states() == stored_item_states

    cis.save()
    assert (store.save_object_to_file.call_args  # type: ignore[attr-defined]
            is None)  # not called, nothing changed

    cis.clear_item_state("this-key-does-not-exist-anyway")  # no-op, but qualifies as a 'change'
    cis.save()
    assert (store.save_object_to_file.call_args  # type: ignore[attr-defined]
            is not None)
    assert store.save_object_to_file.call_args.args[1] == stored_item_states

    # remove key
    cis.clear_item_state("stored-user-key-1")
    cis.save()
    assert store.save_object_to_file.call_args is not None
    assert store.save_object_to_file.call_args.args[1] == {test_prefix + ("stored-user-key-2",): 42}

    # bring back key
    cis.set_item_state("stored-user-key-1", 42)
    cis.save()
    assert store.save_object_to_file.call_args is not None
    assert store.save_object_to_file.call_args.args[1] == {
        test_prefix + ("stored-user-key-1",): 42,
        test_prefix + ("stored-user-key-2",): 42,
    }

    cis.clear_item_state("stored-user-key-1")
    cis.save()
    assert store.save_object_to_file.call_args is not None
    assert store.save_object_to_file.call_args.args[1] == {test_prefix + ("stored-user-key-2",): 42}
