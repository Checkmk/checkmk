#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import brocade_optical
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.utils import interfaces


@pytest.mark.parametrize(
    "params, expect_service",
    [
        (
            [(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
            True,
        ),
        (
            [
                {
                    "discovery_single": (False, {}),
                    "matching_conditions": (True, {}),
                },
                (interfaces.DISCOVERY_DEFAULT_PARAMETERS),
            ],
            False,
        ),
        (
            [
                {
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "alias",
                            "pad_portnumbers": True,
                        },
                    ),
                    "matching_conditions": (
                        False,
                        {"porttypes": ["6"], "portstates": ["1", "3"]},
                    ),
                },
                (interfaces.DISCOVERY_DEFAULT_PARAMETERS),
            ],
            True,
        ),
        (
            [
                {
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "index",
                            "pad_portnumbers": True,
                        },
                    ),
                    "matching_conditions": (
                        False,
                        {"match_desc": ["10GigabitEthernet"]},
                    ),
                },
                (interfaces.DISCOVERY_DEFAULT_PARAMETERS),
            ],
            True,
        ),
    ],
)
def test_discover_brocade_optical(params, expect_service) -> None:
    section: brocade_optical.Section = {
        "1410": {
            "description": "10GigabitEthernet23/2",
            "operational_status": "1",
            "part": "57-0000076-01",
            "port_type": "6",
            "rx_light": (-36.9897, "Low-Alarm"),
            "serial": "ADF2094300014UN",
            "temp": (31.4882, "Normal"),
            "tx_light": (-1.4508, "Normal"),
            "type": "10GE LR 10km SFP+",
        }
    }
    services = [Service(item="1410", parameters={}, labels=[])]
    assert list(
        brocade_optical.discover_brocade_optical(
            params,
            section,
        )
    ) == (expect_service and services or [])


@pytest.mark.parametrize(
    "item,params,section,expected",
    [
        (
            "001410",
            {},
            {
                "1410": {
                    "description": "10GigabitEthernet23/2",
                    "operational_status": "2",
                    "part": "57-0000076-01",
                    "port_type": "6",
                    "rx_light": (-36.9897, "Low-Alarm"),
                    "serial": "ADF2094300014UN",
                    "temp": (31.4882, "Normal"),
                    "tx_light": (-1.4508, "Normal"),
                    "type": "10GE LR 10km SFP+",
                }
            },
            [
                Result(
                    state=state.OK,
                    summary="[S/N ADF2094300014UN, P/N 57-0000076-01] Operational down",
                ),
                Metric("temp", 31.4882),
                Result(state=state.OK, summary="Temperature: 31.5°C"),
                Result(
                    state=state.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
                Result(state=state.OK, summary="TX Light -1.5 dBm (Normal)"),
                Metric("tx_light", -1.4508),
                Result(state=state.OK, summary="RX Light -37.0 dBm (Low-Alarm)"),
                Metric("rx_light", -36.9897),
            ],
        ),
        (
            "1409",
            {"rx_light": True, "tx_light": True, "lanes": True},
            {
                "1409": {
                    "description": "10GigabitEthernet23/1",
                    "lanes": {
                        1: {
                            "rx_light": (-2.2504, "Normal"),
                            "temp": (31.4531, "Normal"),
                            "tx_light": (-1.6045, "Normal"),
                        }
                    },
                    "operational_status": "1",
                    "part": "57-0000076-01",
                    "port_type": "6",
                    "rx_light": (-2.2504, "Normal"),
                    "serial": "ADF2094300014TL",
                    "temp": (None, None),
                    "tx_light": (-1.6045, "Normal"),
                    "type": "10GE LR 10km SFP+",
                }
            },
            [
                Result(
                    state=state.OK,
                    summary="[S/N ADF2094300014TL, P/N 57-0000076-01] Operational up",
                ),
                Result(state=state.OK, summary="TX Light -1.6 dBm (Normal)"),
                Metric("tx_light", -1.6045),
                Result(state=state.OK, summary="RX Light -2.3 dBm (Normal)"),
                Metric("rx_light", -2.2504),
                Result(state=state.OK, notice="Temperature (Lane 1) Temperature: 31.5°C"),
                Metric("port_temp_1", 31.4531),
                Result(state=state.OK, notice="TX Light (Lane 1) -1.6 dBm (Normal)"),
                Metric("tx_light_1", -1.6045),
                Result(state=state.OK, notice="RX Light (Lane 1) -2.3 dBm (Normal)"),
                Metric("rx_light_1", -2.2504),
            ],
        ),
    ],
)
def test_check_brocade_optical(item, params, section, expected) -> None:
    assert list(brocade_optical.check_brocade_optical(item, params, section)) == expected


# Disable yapf here as it takes ages
# yapf: disable
@pytest.mark.parametrize('string_table, discovery_results, items_params_results', [
    (
        [
            [[u'1', u'10GigabitEthernet1/1/1', u'6', u'1'],
             [u'2', u'10GigabitEthernet1/1/2', u'6', u'2'],
             [u'3', u'10GigabitEthernet1/1/3', u'6', u'1'],
             [u'4', u'10GigabitEthernet1/1/4', u'6', u'2'],
             [u'5', u'10GigabitEthernet1/1/5', u'6', u'1'],
             [u'6', u'10GigabitEthernet1/1/6', u'6', u'2'],
             [u'7', u'10GigabitEthernet1/1/7', u'6', u'1'],
             [u'8', u'10GigabitEthernet1/1/8', u'6', u'2'],
             [u'9', u'10GigabitEthernet1/1/9', u'6', u'1'],
             [u'10', u'10GigabitEthernet1/1/10', u'6', u'2'],
             [u'11', u'10GigabitEthernet1/1/11', u'6', u'1'],
             [u'12', u'10GigabitEthernet1/1/12', u'6', u'2'],
             [u'13', u'10GigabitEthernet1/1/13', u'6', u'2'],
             [u'14', u'10GigabitEthernet1/1/14', u'6', u'2'],
             [u'15', u'10GigabitEthernet1/1/15', u'6', u'2'],
             [u'16', u'10GigabitEthernet1/1/16', u'6', u'2'],
             [u'17', u'10GigabitEthernet1/1/17', u'6', u'2'],
             [u'18', u'10GigabitEthernet1/1/18', u'6', u'2'],
             [u'19', u'10GigabitEthernet1/1/19', u'6', u'2'],
             [u'20', u'10GigabitEthernet1/1/20', u'6', u'2'],
             [u'21', u'10GigabitEthernet1/1/21', u'6', u'2'],
             [u'22', u'10GigabitEthernet1/1/22', u'6', u'2'],
             [u'23', u'10GigabitEthernet1/1/23', u'6', u'2'],
             [u'24', u'10GigabitEthernet1/1/24', u'6', u'2'],
             [u'25', u'10GigabitEthernet1/1/25', u'6', u'2'],
             [u'26', u'10GigabitEthernet1/1/26', u'6', u'2'],
             [u'27', u'10GigabitEthernet1/1/27', u'6', u'2'],
             [u'28', u'10GigabitEthernet1/1/28', u'6', u'2'],
             [u'29', u'10GigabitEthernet1/1/29', u'6', u'2'],
             [u'30', u'10GigabitEthernet1/1/30', u'6', u'2'],
             [u'31', u'10GigabitEthernet1/1/31', u'6', u'2'],
             [u'32', u'10GigabitEthernet1/1/32', u'6', u'2'],
             [u'33', u'10GigabitEthernet1/1/33', u'6', u'2'],
             [u'34', u'10GigabitEthernet1/1/34', u'6', u'2'],
             [u'35', u'10GigabitEthernet1/1/35', u'6', u'2'],
             [u'36', u'10GigabitEthernet1/1/36', u'6', u'2'],
             [u'37', u'10GigabitEthernet1/1/37', u'6', u'2'],
             [u'38', u'10GigabitEthernet1/1/38', u'6', u'2'],
             [u'39', u'10GigabitEthernet1/1/39', u'6', u'2'],
             [u'40', u'10GigabitEthernet1/1/40', u'6', u'2'],
             [u'41', u'10GigabitEthernet1/1/41', u'6', u'2'],
             [u'42', u'10GigabitEthernet1/1/42', u'6', u'2'],
             [u'43', u'10GigabitEthernet1/1/43', u'6', u'2'],
             [u'44', u'10GigabitEthernet1/1/44', u'6', u'2'],
             [u'45', u'10GigabitEthernet1/1/45', u'6', u'2'],
             [u'46', u'10GigabitEthernet1/1/46', u'6', u'2'],
             [u'47', u'10GigabitEthernet1/1/47', u'6', u'2'],
             [u'48', u'10GigabitEthernet1/1/48', u'6', u'2'], [u'49', u'Management', u'6', u'2'],
             [u'65', u'40GigabitEthernet1/2/1', u'6', u'1'],
             [u'69', u'40GigabitEthernet1/2/2', u'6', u'2'],
             [u'73', u'40GigabitEthernet1/2/3', u'6', u'2'],
             [u'77', u'40GigabitEthernet1/2/4', u'6', u'1'],
             [u'81', u'40GigabitEthernet1/2/5', u'6', u'2'],
             [u'85', u'40GigabitEthernet1/2/6', u'6', u'2'],
             [u'129', u'40GigabitEthernet1/3/1', u'6', u'1'],
             [u'133', u'40GigabitEthernet1/3/2', u'6', u'2'],
             [u'137', u'40GigabitEthernet1/3/3', u'6', u'2'],
             [u'141', u'40GigabitEthernet1/3/4', u'6', u'2'],
             [u'145', u'40GigabitEthernet1/3/5', u'6', u'2'],
             [u'149', u'40GigabitEthernet1/3/6', u'6', u'2'],
             [u'257', u'10GigabitEthernet2/1/1', u'6', u'1'],
             [u'258', u'10GigabitEthernet2/1/2', u'6', u'2'],
             [u'259', u'10GigabitEthernet2/1/3', u'6', u'1'],
             [u'260', u'10GigabitEthernet2/1/4', u'6', u'2'],
             [u'261', u'10GigabitEthernet2/1/5', u'6', u'1'],
             [u'262', u'10GigabitEthernet2/1/6', u'6', u'2'],
             [u'263', u'10GigabitEthernet2/1/7', u'6', u'1'],
             [u'264', u'10GigabitEthernet2/1/8', u'6', u'2'],
             [u'265', u'10GigabitEthernet2/1/9', u'6', u'1'],
             [u'266', u'10GigabitEthernet2/1/10', u'6', u'2'],
             [u'267', u'10GigabitEthernet2/1/11', u'6', u'1'],
             [u'268', u'10GigabitEthernet2/1/12', u'6', u'2'],
             [u'269', u'10GigabitEthernet2/1/13', u'6', u'2'],
             [u'270', u'10GigabitEthernet2/1/14', u'6', u'2'],
             [u'271', u'10GigabitEthernet2/1/15', u'6', u'2'],
             [u'272', u'10GigabitEthernet2/1/16', u'6', u'2'],
             [u'273', u'10GigabitEthernet2/1/17', u'6', u'2'],
             [u'274', u'10GigabitEthernet2/1/18', u'6', u'2'],
             [u'275', u'10GigabitEthernet2/1/19', u'6', u'2'],
             [u'276', u'10GigabitEthernet2/1/20', u'6', u'2'],
             [u'277', u'10GigabitEthernet2/1/21', u'6', u'2'],
             [u'278', u'10GigabitEthernet2/1/22', u'6', u'2'],
             [u'279', u'10GigabitEthernet2/1/23', u'6', u'2'],
             [u'280', u'10GigabitEthernet2/1/24', u'6', u'2'],
             [u'281', u'10GigabitEthernet2/1/25', u'6', u'2'],
             [u'282', u'10GigabitEthernet2/1/26', u'6', u'2'],
             [u'283', u'10GigabitEthernet2/1/27', u'6', u'2'],
             [u'284', u'10GigabitEthernet2/1/28', u'6', u'2'],
             [u'285', u'10GigabitEthernet2/1/29', u'6', u'2'],
             [u'286', u'10GigabitEthernet2/1/30', u'6', u'2'],
             [u'287', u'10GigabitEthernet2/1/31', u'6', u'2'],
             [u'288', u'10GigabitEthernet2/1/32', u'6', u'2'],
             [u'289', u'10GigabitEthernet2/1/33', u'6', u'2'],
             [u'290', u'10GigabitEthernet2/1/34', u'6', u'2'],
             [u'291', u'10GigabitEthernet2/1/35', u'6', u'2'],
             [u'292', u'10GigabitEthernet2/1/36', u'6', u'2'],
             [u'293', u'10GigabitEthernet2/1/37', u'6', u'2'],
             [u'294', u'10GigabitEthernet2/1/38', u'6', u'2'],
             [u'295', u'10GigabitEthernet2/1/39', u'6', u'2'],
             [u'296', u'10GigabitEthernet2/1/40', u'6', u'2'],
             [u'297', u'10GigabitEthernet2/1/41', u'6', u'2'],
             [u'298', u'10GigabitEthernet2/1/42', u'6', u'2'],
             [u'299', u'10GigabitEthernet2/1/43', u'6', u'2'],
             [u'300', u'10GigabitEthernet2/1/44', u'6', u'2'],
             [u'301', u'10GigabitEthernet2/1/45', u'6', u'2'],
             [u'302', u'10GigabitEthernet2/1/46', u'6', u'2'],
             [u'303', u'10GigabitEthernet2/1/47', u'6', u'2'],
             [u'304', u'10GigabitEthernet2/1/48', u'6', u'2'],
             [u'321', u'40GigabitEthernet2/2/1', u'6', u'1'],
             [u'325', u'40GigabitEthernet2/2/2', u'6', u'2'],
             [u'329', u'40GigabitEthernet2/2/3', u'6', u'2'],
             [u'333', u'40GigabitEthernet2/2/4', u'6', u'1'],
             [u'337', u'40GigabitEthernet2/2/5', u'6', u'2'],
             [u'341', u'40GigabitEthernet2/2/6', u'6', u'2'],
             [u'385', u'40GigabitEthernet2/3/1', u'6', u'1'],
             [u'389', u'40GigabitEthernet2/3/2', u'6', u'1'],
             [u'393', u'40GigabitEthernet2/3/3', u'6', u'2'],
             [u'397', u'40GigabitEthernet2/3/4', u'6', u'2'],
             [u'401', u'40GigabitEthernet2/3/5', u'6', u'2'],
             [u'405', u'40GigabitEthernet2/3/6', u'6', u'2'], [u'3073', u'lg1', u'6', u'1'],
             [u'3074', u'lg2', u'6', u'1'], [u'3075', u'lg3', u'6', u'1'],
             [u'3076', u'lg4', u'6', u'1'], [u'3077', u'lg5', u'6', u'1'],
             [u'3078', u'lg6', u'6', u'1'], [u'3079', u'lg7', u'6', u'1'],
             [u'16777217', u'v30', u'135', u'1']],
            [],
            [],
            [[u'28.5273 C Normal', u'-002.2373 dBm Normal', u'-002.4298 dBm Normal', u'3.1'],
             [u'28.8945 C Normal', u'-002.2848 dBm Normal', u'-002.3597 dBm Normal', u'5.1'],
             [u'29.3554 C Normal', u'-002.2944 dBm Normal', u'-002.8474 dBm Normal', u'7.1'],
             [u'28.2851 C Normal', u'-002.2789 dBm Normal', u'-002.7278 dBm Normal', u'9.1'],
             [u'26.0507 C Normal', u'-002.2848 dBm Normal', u'-004.1953 dBm Normal', u'11.1'],
             [u'25.5468 C Normal', u'-002.2723 dBm Normal', u'-002.3942 dBm Normal', u'259.1'],
             [u'26.5156 C Normal', u'-002.2635 dBm Normal', u'-002.4116 dBm Normal', u'261.1'],
             [u'27.7500 C Normal', u'-002.2672 dBm Normal', u'-002.2760 dBm Normal', u'263.1'],
             [u'25.4765 C Normal', u'-002.2519 dBm Normal', u'-002.1331 dBm Normal', u'265.1'],
             [u'26.9257 C Normal', u'-002.2716 dBm Normal', u'-002.5251 dBm Normal', u'267.1'],
             [u'', u'', u'', u'321.1'], [u'', u'', u'', u'321.2'], [u'', u'', u'', u'321.3'],
             [u'', u'', u'', u'321.4'], [u'', u'', u'', u'333.1'], [u'', u'', u'', u'333.2'],
             [u'', u'', u'', u'333.3'], [u'', u'', u'', u'333.4']],
        ],
        [],
        [],
    ),
    (
        [
            [[u'1409', u'10GigabitEthernet23/1', u'6', u'1'],
             [u'1410', u'10GigabitEthernet23/2', u'6', u'2'],
             [u'1411', u'10GigabitEthernet23/3', u'6', u'2'],
             [u'1412', u'10GigabitEthernet23/4', u'6', u'2'],
             [u'1413', u'10GigabitEthernet23/5', u'6', u'2'],
             [u'1414', u'10GigabitEthernet23/6', u'6', u'2'],
             [u'1415', u'10GigabitEthernet23/7', u'6', u'2'],
             [u'1416', u'10GigabitEthernet23/8', u'6', u'2'],
             [u'1473', u'10GigabitEthernet24/1', u'6', u'2'],
             [u'1474', u'10GigabitEthernet24/2', u'6', u'2'],
             [u'1475', u'10GigabitEthernet24/3', u'6', u'2'],
             [u'1476', u'10GigabitEthernet24/4', u'6', u'2'],
             [u'1477', u'10GigabitEthernet24/5', u'6', u'2'],
             [u'1478', u'10GigabitEthernet24/6', u'6', u'2'],
             [u'1479', u'10GigabitEthernet24/7', u'6', u'2'],
             [u'1480', u'10GigabitEthernet24/8', u'6', u'2'],
             [u'1793', u'10GigabitEthernet29/1', u'6', u'2'],
             [u'1794', u'10GigabitEthernet29/2', u'6', u'2'],
             [u'1795', u'10GigabitEthernet29/3', u'6', u'2'],
             [u'1796', u'10GigabitEthernet29/4', u'6', u'2'],
             [u'1857', u'10GigabitEthernet30/1', u'6', u'1'],
             [u'1858', u'10GigabitEthernet30/2', u'6', u'1'],
             [u'1859', u'10GigabitEthernet30/3', u'6', u'1'],
             [u'1860', u'10GigabitEthernet30/4', u'6', u'1'],
             [u'1921', u'10GigabitEthernet31/1', u'6', u'1'],
             [u'1922', u'10GigabitEthernet31/2', u'6', u'1'],
             [u'1923', u'10GigabitEthernet31/3', u'6', u'1'],
             [u'1924', u'10GigabitEthernet31/4', u'6', u'1'],
             [u'1985', u'10GigabitEthernet32/1', u'6', u'2'],
             [u'1986', u'10GigabitEthernet32/2', u'6', u'2'],
             [u'1987', u'10GigabitEthernet32/3', u'6', u'2'],
             [u'1988', u'10GigabitEthernet32/4', u'6', u'2'],
             [u'2049', u'EthernetManagement1', u'6', u'1'], [u'33554433', u'lb1', u'24', u'1'],
             [u'67108864', u'tnl0', u'150', u'1'], [u'67108865', u'tnl1', u'150', u'1'],
             [u'67108866', u'tnl2', u'150', u'1'], [u'67108867', u'tnl3', u'150', u'1'],
             [u'67108868', u'tnl4', u'150', u'1'], [u'67108869', u'tnl5', u'150', u'1'],
             [u'67108870', u'tnl6', u'150', u'1'], [u'67108871', u'tnl7', u'150', u'1'],
             [u'67108872', u'tnl8', u'150', u'1'], [u'67108873', u'tnl9', u'150', u'1'],
             [u'67108874', u'tnl10', u'150', u'1'], [u'67108875', u'tnl11', u'150', u'1'],
             [u'67108876', u'tnl12', u'150', u'1'], [u'67108877', u'tnl13', u'150', u'1'],
             [u'67108878', u'tnl14', u'150', u'1'], [u'67108879', u'tnl15', u'150', u'1'],
             [u'67108880', u'tnl16', u'150', u'1'], [u'67108881', u'tnl17', u'150', u'1'],
             [u'67108882', u'tnl18', u'150', u'1'], [u'67108883', u'tnl19', u'150', u'1'],
             [u'67108884', u'tnl20', u'150', u'1'], [u'67108885', u'tnl21', u'150', u'1'],
             [u'67108886', u'tnl22', u'150', u'1'], [u'67108887', u'tnl23', u'150', u'1'],
             [u'67108888', u'tnl24', u'150', u'1'], [u'67108889', u'tnl25', u'150', u'1'],
             [u'67108890', u'tnl26', u'150', u'1'], [u'67108891', u'tnl27', u'150', u'1'],
             [u'67108892', u'tnl28', u'150', u'1'], [u'67108893', u'tnl29', u'150', u'1'],
             [u'67108894', u'tnl30', u'150', u'1'], [u'67108895', u'tnl31', u'150', u'1'],
             [u'67108896', u'tnl32', u'150', u'1'], [u'67108897', u'tnl33', u'150', u'1'],
             [u'67108898', u'tnl34', u'150', u'1'], [u'67108899', u'tnl35', u'150', u'1'],
             [u'67108900', u'tnl36', u'150', u'1'], [u'67108901', u'tnl37', u'150', u'1'],
             [u'67108902', u'tnl38', u'150', u'1'], [u'67108903', u'tnl39', u'150', u'1'],
             [u'67108904', u'tnl40', u'150', u'1'], [u'67108905', u'tnl41', u'150', u'1'],
             [u'67108906', u'tnl42', u'150', u'1'], [u'67108907', u'tnl43', u'150', u'1'],
             [u'67108908', u'tnl44', u'150', u'1'], [u'67108909', u'tnl45', u'150', u'1'],
             [u'67108910', u'tnl46', u'150', u'1'], [u'67108911', u'tnl47', u'150', u'1'],
             [u'67108912', u'tnl48', u'150', u'1'], [u'67108913', u'tnl49', u'150', u'1'],
             [u'67108914', u'tnl50', u'150', u'1'], [u'67108915', u'tnl51', u'150', u'1'],
             [u'67108916', u'tnl52', u'150', u'1'], [u'67108917', u'tnl53', u'150', u'1'],
             [u'67108918', u'tnl54', u'150', u'1'], [u'67108919', u'tnl55', u'150', u'1'],
             [u'67108920', u'tnl56', u'150', u'1'], [u'67108921', u'tnl57', u'150', u'1'],
             [u'67108922', u'tnl58', u'150', u'1'], [u'67108923', u'tnl59', u'150', u'1'],
             [u'67108924', u'tnl60', u'150', u'1'], [u'67108925', u'tnl61', u'150', u'1'],
             [u'67108926', u'tnl62', u'150', u'1'], [u'67108927', u'tnl63', u'150', u'1'],
             [u'67108928', u'tnl64', u'150', u'1'], [u'67108929', u'tnl65', u'150', u'1'],
             [u'67108930', u'tnl66', u'150', u'1'], [u'67108931', u'tnl67', u'150', u'1'],
             [u'67108932', u'tnl68', u'150', u'1'], [u'67108933', u'tnl69', u'150', u'1'],
             [u'67108934', u'tnl70', u'150', u'1'], [u'67108935', u'tnl71', u'150', u'1'],
             [u'67108936', u'tnl72', u'150', u'1'], [u'67108937', u'tnl73', u'150', u'1'],
             [u'67108938', u'tnl74', u'150', u'1'], [u'67108939', u'tnl75', u'150', u'1'],
             [u'83886081', u'LAG1', u'202', u'1'], [u'83886083', u'LAG3', u'202', u'1'],
             [u'83886085', u'LAG5', u'202', u'2']],
            [[u'      N/A    ', u'-001.6045 dBm: Normal', u'-002.2504 dBm: Normal', u'1409'],
             [u'31.4882 C: Normal', u'-001.4508 dBm: Normal', u'-036.9897 dBm: Low-Alarm', u'1410'],
             [u'31.4531 C: Normal', u'-001.4194 dBm: Normal', u'-033.9794 dBm: Low-Alarm', u'1411'],
             [
                 u'29.5703 C: Normal', u'-031.5490 dBm: Low-Alarm', u'-036.9897 dBm: Low-Alarm',
                 u'1412'
             ],
             [
                 u'28.7187 C: Normal', u'-033.0102 dBm: Low-Alarm', u'-214748.3647 dBm: Low-Alarm',
                 u'1413'
             ],
             [
                 u'31.5898 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1414'
             ],
             [
                 u'27.6054 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1415'
             ],
             [
                 u'28.6132 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1416'
             ],
             [
                 u'31.5078 C: Normal', u'-214748.3647 dBm: Low-Alarm', u'-019.2081 dBm: Low-Alarm',
                 u'1473'
             ],
             [
                 u'28.5000 C: Normal', u'-029.5860 dBm: Low-Alarm', u'-214748.3647 dBm: Low-Alarm',
                 u'1474'
             ],
             [
                 u'28.9414 C: Normal', u'-032.2184 dBm: Low-Alarm', u'-214748.3647 dBm: Low-Alarm',
                 u'1475'
             ],
             [
                 u'30.2695 C: Normal', u'-029.2081 dBm: Low-Alarm', u'-214748.3647 dBm: Low-Alarm',
                 u'1476'
             ],
             [
                 u'29.5664 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1477'
             ],
             [
                 u'33.2578 C: Normal', u'-031.5490 dBm: Low-Alarm', u'-214748.3647 dBm: Low-Alarm',
                 u'1478'
             ],
             [
                 u'28.3906 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1479'
             ],
             [
                 u'30.1679 C: Normal', u'-035.2287 dBm: Low-Alarm', u'-214748.3647 dBm: Low-Alarm',
                 u'1480'
             ],
             [
                 u'30.7304 C: Normal', u'-214748.3647 dBm: Low-Alarm', u'-040.0000 dBm: Low-Alarm',
                 u'1793'
             ],
             [
                 u'29.0546 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1794'
             ],
             [
                 u'33.4609 C: Normal', u'-214748.3647 dBm: Low-Alarm', u'-040.0000 dBm: Low-Alarm',
                 u'1795'
             ],
             [
                 u'31.5429 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1796'
             ],
             [u'31.7695 C: Normal', u'001.4924 dBm: Normal', u'-004.6711 dBm: High-Alarm', u'1857'],
             [u'34.8203 C: Normal', u'001.7943 dBm: Normal', u'-005.2841 dBm: High-Warn', u'1858'],
             [u'34.1445 C: Normal', u'001.7117 dBm: Normal', u'-004.4117 dBm: High-Warn', u'1859'],
             [u'33.2734 C: Normal', u'001.9810 dBm: Normal', u'-003.8048 dBm: High-Alarm', u'1860'],
             [u'28.9570 C: Normal', u'002.0002 dBm: Normal', u'-015.6224 dBm: Normal', u'1921'],
             [u'30.7734 C: Normal', u'000.9642 dBm: Normal', u'-015.2143 dBm: Normal', u'1922'],
             [u'32.6914 C: Normal', u'001.7545 dBm: Normal', u'-014.8811 dBm: Normal', u'1923'],
             [u'32.5000 C: Normal', u'001.3653 dBm: Normal', u'-015.4515 dBm: Normal', u'1924'],
             [
                 u'27.4179 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1985'
             ],
             [
                 u'29.5898 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1986'
             ],
             [
                 u'32.8593 C: Normal', u'-214748.3647 dBm: Low-Alarm', u'-035.2287 dBm: Low-Alarm',
                 u'1987'
             ],
             [
                 u'29.7226 C: Normal', u'-214748.3647 dBm: Low-Alarm',
                 u'-214748.3647 dBm: Low-Alarm', u'1988'
             ]],
            [[u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094300014TL', u'1409'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094300014UN', u'1410'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094300014UL', u'1411'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094300014UP', u'1412'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094600003A9', u'1413'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094400005FT', u'1414'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094600003AF', u'1415'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF209450000MT2', u'1416'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADA111253005111', u'1473'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094500003VL', u'1474'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094500003UJ', u'1475'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF20945000041J', u'1476'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094400005FS', u'1477'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094500003VD', u'1478'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094500003VH', u'1479'],
             [u'10GE LR 10km SFP+', u'57-0000076-01', u'ADF2094400012DM', u'1480'],
             [u'10GBASE-ZRD 1538.20nm (XFP)', u'FTRX-3811-349-F1', u'AG601D6', u'1793'],
             [u'10GBASE-ZRD 1537.40nm (XFP)', u'FIM31060/210W50', u'SNG031', u'1794'],
             [u'10GBASE-ZRD 1536.60nm (XFP)', u'FTRX-3811-351-F1', u'AG601Y8', u'1795'],
             [u'10GBASE-ZRD 1535.80nm (XFP)', u'XFP-DWLR08-52', u'UL30HQ4', u'1796'],
             [u'10GBASE-ZRD 1535.05nm (XFP)', u'FTRX-3811-353-F1', u'AGA07AJ', u'1857'],
             [u'10GBASE-ZRD 1534.25nm (XFP)', u'FTRX-3811-354-F1', u'AG800UB', u'1858'],
             [u'10GBASE-ZRD 1533.45nm (XFP)', u'FIM31060/210W55', u'PRG041', u'1859'],
             [u'10GBASE-ZRD 1532.70nm (XFP)', u'FIM31060/210W56', u'SPG153', u'1860'],
             [u'10GBASE-ZRD 1538.20nm (XFP)', u'FIM31060/210W49', u'PHG011', u'1921'],
             [u'10GBASE-ZRD 1537.40nm (XFP)', u'FIM31060/210W50', u'PHG020', u'1922'],
             [u'10GBASE-ZRD 1536.60nm (XFP)', u'FIM31060/210W51', u'PRG015', u'1923'],
             [u'10GBASE-ZRD 1535.80nm (XFP)', u'XFP-DWLR08-52', u'UL30HQ5', u'1924'],
             [u'10GBASE-ZRD 1535.05nm (XFP)', u'FTRX-3811-353-F1', u'AFS0064', u'1985'],
             [u'10GBASE-ZRD 1534.25nm (XFP)', u'XFP-DWLR08-54', u'UKR0NE8', u'1986'],
             [u'10GBASE-ZRD 1533.45nm (XFP)', u'FTRX-3811-355-F1', u'AG705BX', u'1987'],
             [u'10GBASE-ZRD 1532.70nm (XFP)', u'FIM31060/210W56', u'SPG084', u'1988']],
            [],
        ],
        [
            Service(item='1409', parameters={}, labels=[]),
            Service(item='1857', parameters={}, labels=[]),
            Service(item='1858', parameters={}, labels=[]),
            Service(item='1859', parameters={}, labels=[]),
            Service(item='1860', parameters={}, labels=[]),
            Service(item='1921', parameters={}, labels=[]),
            Service(item='1922', parameters={}, labels=[]),
            Service(item='1923', parameters={}, labels=[]),
            Service(item='1924', parameters={}, labels=[]),
        ],
        [
            (
                '1409',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N ADF2094300014TL, P/N 57-0000076-01] Operational up',
                           details='[S/N ADF2094300014TL, P/N 57-0000076-01] Operational up'),
                    Result(state=state.OK,
                           summary='TX Light -1.6 dBm (Normal)',
                           details='TX Light -1.6 dBm (Normal)'),
                    Metric('tx_light', -1.6045),
                    Result(state=state.OK,
                           summary='RX Light -2.3 dBm (Normal)',
                           details='RX Light -2.3 dBm (Normal)'),
                    Metric('rx_light', -2.2504),
                ],
            ),
            (
                '1857',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N AGA07AJ, P/N FTRX-3811-353-F1] Operational up',
                           details='[S/N AGA07AJ, P/N FTRX-3811-353-F1] Operational up'),
                    Metric('temp', 31.7695),
                    Result(state=state.OK,
                           summary='Temperature: 31.8°C',
                           details='Temperature: 31.8°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 1.5 dBm (Normal)',
                           details='TX Light 1.5 dBm (Normal)'),
                    Metric('tx_light', 1.4924),
                    Result(state=state.OK,
                           summary='RX Light -4.7 dBm (High-Alarm)',
                           details='RX Light -4.7 dBm (High-Alarm)'),
                    Metric('rx_light', -4.6711),
                ],
            ),
            (
                '1858',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N AG800UB, P/N FTRX-3811-354-F1] Operational up',
                           details='[S/N AG800UB, P/N FTRX-3811-354-F1] Operational up'),
                    Metric('temp', 34.8203),
                    Result(state=state.OK,
                           summary='Temperature: 34.8°C',
                           details='Temperature: 34.8°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 1.8 dBm (Normal)',
                           details='TX Light 1.8 dBm (Normal)'),
                    Metric('tx_light', 1.7943),
                    Result(state=state.OK,
                           summary='RX Light -5.3 dBm (High-Warn)',
                           details='RX Light -5.3 dBm (High-Warn)'),
                    Metric('rx_light', -5.2841),
                ],
            ),
            (
                '1859',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N PRG041, P/N FIM31060/210W55] Operational up',
                           details='[S/N PRG041, P/N FIM31060/210W55] Operational up'),
                    Metric('temp', 34.1445),
                    Result(state=state.OK,
                           summary='Temperature: 34.1°C',
                           details='Temperature: 34.1°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 1.7 dBm (Normal)',
                           details='TX Light 1.7 dBm (Normal)'),
                    Metric('tx_light', 1.7117),
                    Result(state=state.OK,
                           summary='RX Light -4.4 dBm (High-Warn)',
                           details='RX Light -4.4 dBm (High-Warn)'),
                    Metric('rx_light', -4.4117),
                ],
            ),
            (
                '1860',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N SPG153, P/N FIM31060/210W56] Operational up',
                           details='[S/N SPG153, P/N FIM31060/210W56] Operational up'),
                    Metric('temp', 33.2734),
                    Result(state=state.OK,
                           summary='Temperature: 33.3°C',
                           details='Temperature: 33.3°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 2.0 dBm (Normal)',
                           details='TX Light 2.0 dBm (Normal)'),
                    Metric('tx_light', 1.981),
                    Result(state=state.OK,
                           summary='RX Light -3.8 dBm (High-Alarm)',
                           details='RX Light -3.8 dBm (High-Alarm)'),
                    Metric('rx_light', -3.8048),
                ],
            ),
            (
                '1922',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N PHG020, P/N FIM31060/210W50] Operational up',
                           details='[S/N PHG020, P/N FIM31060/210W50] Operational up'),
                    Metric('temp', 30.7734),
                    Result(state=state.OK,
                           summary='Temperature: 30.8°C',
                           details='Temperature: 30.8°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 1.0 dBm (Normal)',
                           details='TX Light 1.0 dBm (Normal)'),
                    Metric('tx_light', 0.9642),
                    Result(state=state.OK,
                           summary='RX Light -15.2 dBm (Normal)',
                           details='RX Light -15.2 dBm (Normal)'),
                    Metric('rx_light', -15.2143),
                ],
            ),
            (
                '1923',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N PRG015, P/N FIM31060/210W51] Operational up',
                           details='[S/N PRG015, P/N FIM31060/210W51] Operational up'),
                    Metric('temp', 32.6914),
                    Result(state=state.OK,
                           summary='Temperature: 32.7°C',
                           details='Temperature: 32.7°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 1.8 dBm (Normal)',
                           details='TX Light 1.8 dBm (Normal)'),
                    Metric('tx_light', 1.7545),
                    Result(state=state.OK,
                           summary='RX Light -14.9 dBm (Normal)',
                           details='RX Light -14.9 dBm (Normal)'),
                    Metric('rx_light', -14.8811),
                ],
            ),
            (
                '1924',
                {},
                [
                    Result(state=state.OK,
                           summary='[S/N UL30HQ5, P/N XFP-DWLR08-52] Operational up',
                           details='[S/N UL30HQ5, P/N XFP-DWLR08-52] Operational up'),
                    Metric('temp', 32.5),
                    Result(state=state.OK,
                           summary='Temperature: 32.5°C',
                           details='Temperature: 32.5°C'),
                    Result(
                        state=state.OK,
                        notice=
                        'Configuration: prefer user levels over device levels (no levels found)'),
                    Result(state=state.OK,
                           summary='TX Light 1.4 dBm (Normal)',
                           details='TX Light 1.4 dBm (Normal)'),
                    Metric('tx_light', 1.3653),
                    Result(state=state.OK,
                           summary='RX Light -15.5 dBm (Normal)',
                           details='RX Light -15.5 dBm (Normal)'),
                    Metric('rx_light', -15.4515),
                ],
            ),
        ],
    )
])
# yapf: enable
def test_regression(
    string_table,
    discovery_results,
    items_params_results,
):
    section = brocade_optical.parse_brocade_optical(string_table)

    assert (
        list(
            brocade_optical.discover_brocade_optical(
                [(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
                section,
            )
        )
        == discovery_results
    )

    for item, par, res in items_params_results:
        assert (
            list(
                brocade_optical.check_brocade_optical(
                    item,
                    (par),
                    section,
                )
            )
            == res
        )
