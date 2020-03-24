#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.api.agent_based.checking_types import (
    Parameters,
    ServiceLabel,
    Service,
)


@pytest.mark.parametrize("data", [
    None,
    (),
    [],
    "",
])
def test_paramters_invalid(data):
    with pytest.raises(TypeError, match="expected dict"):
        _ = Parameters(data)


def test_parameters_features():
    par0 = Parameters({})
    par1 = Parameters({'olaf': 'schneemann'})

    assert len(par0) == 0
    assert len(par1) == 1

    assert not par0
    assert par1

    assert 'olaf' not in par0
    assert 'olaf' in par1

    assert par0.get('olaf') is None
    assert par1.get('olaf') == 'schneemann'

    with pytest.raises(KeyError):
        _ = par0['olaf']
    assert par1['olaf'] == 'schneemann'

    assert list(par0) == list(par0.keys()) == list(par0.values()) == list(par0.items()) == []
    assert list(par1) == list(par1.keys()) == ['olaf']
    assert list(par1.values()) == ['schneemann']
    assert list(par1.items()) == [('olaf', 'schneemann')]


def test_service_label():
    # as far as the API is concerned, the only important thing ist that they
    # exist, an can be created like this.
    _ = ServiceLabel('from-home-office', 'true')


@pytest.mark.parametrize("item, parameters, labels", [
    (4, None, None),
    (None, (80, 90), None),
    (None, None, ()),
    (None, None, ["foo:bar"]),
])
def test_service_invalid(item, parameters, labels):
    with pytest.raises(TypeError):
        _ = Service(item=item, parameters=parameters, labels=labels)


def test_service_kwargs_only():
    with pytest.raises(TypeError):
        _ = Service(None)  # pylint: disable=too-many-function-args


def test_service_features():
    service = Service(
        item="thingy",
        parameters={"size": 42},
        labels=[ServiceLabel("test-thing", "true")],
    )

    assert service.item == "thingy"
    assert service.parameters == {"size": 42}
    assert service.labels == [ServiceLabel("test-thing", "true")]

    assert repr(service) == ("Service(item='thingy', parameters={'size': 42},"
                             " labels=[ServiceLabel('test-thing', 'true')])")
