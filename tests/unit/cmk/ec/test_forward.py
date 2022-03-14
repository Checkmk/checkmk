#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ec.forward import (
    StructuredData,
    StructuredDataID,
    StructuredDataName,
    StructuredDataParameters,
    StructuredDataValue,
    SyslogMessage,
)


class TestStructuredDataName:
    def test_validation_on_init(self) -> None:
        with pytest.raises(ValueError):
            StructuredDataName("cool Name")

    def test_repr(self) -> None:
        assert repr(StructuredDataName("coolName")) == "coolName"


class TestStructuredDataID:
    def test_validation_on_init(self) -> None:
        with pytest.raises(ValueError):
            StructuredDataID("a@b")

    def test_repr(self) -> None:
        assert repr(StructuredDataID("enterprise@123")) == "enterprise@123"

    @pytest.mark.parametrize(
        "id_, expected_result",
        [
            pytest.param(
                "syncAccuracy",
                True,
                id="normal id without enterprise number",
            ),
            pytest.param(
                "Checkmk@123",
                True,
                id="normal id with enterprise number",
            ),
            pytest.param(
                "Checkmk@",
                False,
                id="id with missing enterprise number",
            ),
            pytest.param(
                "Checkmk@1hugo",
                False,
                id="id with invalid enterprise number",
            ),
            pytest.param(
                "Checkmk@1@2",
                False,
                id="id with multiple @",
            ),
        ],
    )
    def test_validate(
        self,
        id_: str,
        expected_result: bool,
    ) -> None:
        assert StructuredDataID._validate(id_) is expected_result


class TestStructuredDataValue:
    def test_validation_on_init(self) -> None:
        with pytest.raises(ValueError):
            StructuredDataValue("x\ny")

    @pytest.mark.parametrize(
        "structured_data_value, expected_result",
        [
            pytest.param(
                StructuredDataValue("some value"),
                "some value",
                id="no escaping",
            ),
            pytest.param(
                StructuredDataValue(r'\tell me, where "is" ]Gandalf'),
                r"\\tell me, where \"is\" \]Gandalf",
                id="with escaping",
            ),
        ],
    )
    def test_repr(
        self,
        structured_data_value: StructuredDataValue,
        expected_result: str,
    ) -> None:
        assert repr(structured_data_value) == expected_result


class TestStructuredDataParameters:
    @pytest.mark.parametrize(
        "structured_data_parameters, expected_result",
        [
            pytest.param(
                StructuredDataParameters({}),
                "",
                id="no parameters",
            ),
            pytest.param(
                StructuredDataParameters(
                    {
                        StructuredDataName("name"): StructuredDataValue("value"),
                    }
                ),
                'name="value"',
                id="one parameter",
            ),
            pytest.param(
                StructuredDataParameters(
                    {
                        StructuredDataName("name1"): StructuredDataValue("value1"),
                        StructuredDataName("name2"): StructuredDataValue("value[2]"),
                        StructuredDataName("hobbits"): StructuredDataValue("isengard"),
                    }
                ),
                r'name1="value1" name2="value[2\]" hobbits="isengard"',
                id="multiple parameters",
            ),
        ],
    )
    def test_repr(
        self,
        structured_data_parameters: StructuredDataParameters,
        expected_result: str,
    ) -> None:
        assert repr(structured_data_parameters) == expected_result


class TestStructuredData:
    @pytest.mark.parametrize(
        "structured_data, expected_result",
        [
            pytest.param(
                StructuredData({}),
                "-",
                id="no data (NILVALUE)",
            ),
            pytest.param(
                StructuredData(
                    {
                        StructuredDataID("exampleSDID@32473"): StructuredDataParameters({}),
                    }
                ),
                "[exampleSDID@32473]",
                id="one element with id only",
            ),
            pytest.param(
                StructuredData(
                    {
                        StructuredDataID("Checkmk@18662"): StructuredDataParameters(
                            {
                                StructuredDataName("sl"): StructuredDataValue("20"),
                                StructuredDataName("ipaddress"): StructuredDataValue("127.0.0.1"),
                            }
                        ),
                    }
                ),
                '[Checkmk@18662 sl="20" ipaddress="127.0.0.1"]',
                id="one element with id and data",
            ),
            pytest.param(
                StructuredData(
                    {
                        StructuredDataID("examplePriority@32473"): StructuredDataParameters({}),
                        StructuredDataID("Checkmk@18662"): StructuredDataParameters(
                            {
                                StructuredDataName("sl"): StructuredDataValue("20"),
                                StructuredDataName("ipaddress"): StructuredDataValue("127.0.0.1"),
                            }
                        ),
                        StructuredDataID("whatever"): StructuredDataParameters(
                            {
                                StructuredDataName("abc"): StructuredDataValue('x"yz'),
                                StructuredDataName("hurz"): StructuredDataValue("bärz"),
                            }
                        ),
                    }
                ),
                r'[examplePriority@32473][Checkmk@18662 sl="20" ipaddress="127.0.0.1"][whatever abc="x\"yz" hurz="bärz"]',
                id="multiple elements",
            ),
        ],
    )
    def test_repr(
        self,
        structured_data: StructuredData,
        expected_result: str,
    ) -> None:
        assert repr(structured_data) == expected_result


class TestSyslogMessage:
    @pytest.mark.parametrize(
        "facility, severity, stuctured_data",
        [
            pytest.param(
                30,
                2,
                StructuredData({}),
                id="invalid facility",
            ),
            pytest.param(
                3,
                9,
                StructuredData({}),
                id="invalid severity",
            ),
            pytest.param(
                4,
                5,
                StructuredData(
                    {
                        StructuredDataID("Checkmk@18662"): StructuredDataParameters({}),
                    }
                ),
                id="invalid structured data",
            ),
        ],
    )
    def test_init_validation(
        self,
        facility: int,
        severity: int,
        stuctured_data: StructuredData,
    ) -> None:
        with pytest.raises(ValueError):
            SyslogMessage(
                facility=facility,
                severity=severity,
                structured_data=stuctured_data,
            )

    @pytest.mark.parametrize(
        "syslog_message, expected_result",
        [
            pytest.param(
                SyslogMessage(
                    facility=1,
                    severity=2,
                ),
                "<10>1 - - - - - [Checkmk@18662]",
                id="minimal case",
            ),
            pytest.param(
                SyslogMessage(
                    facility=1,
                    severity=2,
                    timestamp=1617864437,
                    host_name="herbert",
                    application="some_deamon",
                    proc_id="procid",
                    msg_id="msgid",
                    structured_data=StructuredData(
                        {
                            StructuredDataID("exampleSDID@32473"): StructuredDataParameters(
                                {
                                    StructuredDataName("iut"): StructuredDataValue("3"),
                                    StructuredDataName("eventSource"): StructuredDataValue(
                                        "Application"
                                    ),
                                }
                            ),
                        }
                    ),
                    text="something is wrong with herbert",
                ),
                '<10>1 2021-04-08T06:47:17+00:00 herbert some_deamon procid msgid [exampleSDID@32473 iut="3" eventSource="Application"][Checkmk@18662] something is wrong with herbert',
                id="standard case, ascii",
            ),
            pytest.param(
                SyslogMessage(
                    facility=1,
                    severity=2,
                    timestamp=1617864437,
                    host_name="herbert",
                    application="some_deamon",
                    proc_id="procid",
                    msg_id="msgid",
                    structured_data=StructuredData(
                        {
                            StructuredDataID("exampleSDID@32473"): StructuredDataParameters(
                                {
                                    StructuredDataName("iut"): StructuredDataValue("3"),
                                    StructuredDataName("eventSource"): StructuredDataValue(
                                        "Application"
                                    ),
                                }
                            ),
                        }
                    ),
                    text="something is wrong with herbert",
                    ip_address="127.0.0.2",
                    service_level=13,
                ),
                '<10>1 2021-04-08T06:47:17+00:00 herbert some_deamon procid msgid [exampleSDID@32473 iut="3" eventSource="Application"][Checkmk@18662 ipaddress="127.0.0.2" sl="13"] something is wrong with herbert',
                id="with ip address and service level, ascii",
            ),
            pytest.param(
                SyslogMessage(
                    facility=1,
                    severity=2,
                    timestamp=1617864437,
                    host_name="herbert",
                    application="some_deamon",
                    proc_id="procid",
                    msg_id="msgid",
                    structured_data=StructuredData(
                        {
                            StructuredDataID("exampleSDID@32473"): StructuredDataParameters(
                                {
                                    StructuredDataName("iut"): StructuredDataValue("3"),
                                    StructuredDataName("eventSource"): StructuredDataValue(
                                        "Application"
                                    ),
                                }
                            ),
                        }
                    ),
                    text="something is wrong with härbört",
                    ip_address="127.0.0.2",
                    service_level=13,
                ),
                '<10>1 2021-04-08T06:47:17+00:00 herbert some_deamon procid msgid [exampleSDID@32473 iut="3" eventSource="Application"][Checkmk@18662 ipaddress="127.0.0.2" sl="13"] \ufeffsomething is wrong with härbört',
                id="with ip address and service level, utf-8",
            ),
            pytest.param(
                SyslogMessage(
                    facility=1,
                    severity=2,
                    timestamp=1617864437.23,
                    host_name="herbert härry",
                    application="somé_deamon",
                    proc_id="ìd",
                    msg_id="mässage",
                    structured_data=StructuredData(
                        {
                            StructuredDataID("exampleSDID@32473"): StructuredDataParameters(
                                {
                                    StructuredDataName("iut"): StructuredDataValue("3"),
                                    StructuredDataName("eventSource"): StructuredDataValue(
                                        "Application"
                                    ),
                                }
                            ),
                            StructuredDataID("needEscaping@123"): StructuredDataParameters(
                                {
                                    StructuredDataName("escapeMe"): StructuredDataValue(r'"abc\]'),
                                }
                            ),
                        }
                    ),
                    text="something is wrong with he\ufeffrbert härry",
                    ip_address="1.2.3.4",
                    service_level=20,
                ),
                r'<10>1 2021-04-08T06:47:17.230000+00:00 - - - - [exampleSDID@32473 iut="3" eventSource="Application"][needEscaping@123 escapeMe="\"abc\\\]"][Checkmk@18662 ipaddress="1.2.3.4" sl="20" host="herbert härry" application="somé_deamon" pid="ìd" msg_id="mässage"]'
                + " \ufeffsomething is wrong with he\ufeffrbert härry",
                id="nothing rfc conform",
            ),
        ],
    )
    def test_repr(
        self,
        syslog_message: SyslogMessage,
        expected_result: str,
    ) -> None:
        assert str(syslog_message) == expected_result
