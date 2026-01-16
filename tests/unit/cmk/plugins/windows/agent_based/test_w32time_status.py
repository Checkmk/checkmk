#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from copy import deepcopy

import pytest

from cmk.agent_based.v2 import (
    Metric,
    Result,
    State,
    StringTable,
)
from cmk.plugins.windows.agent_based import w32time_status
from cmk.plugins.windows.agent_based.w32time_status import DEFAULT_PARAMS

EN_GOOD_SYNC = [
    ["Leap", "Indicator:", "0(no", "warning)"],
    ["Stratum:", "4", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["Precision:", "-23", "(119.209ns", "per", "tick)"],
    ["Root", "Delay:", "0.0000758s"],
    ["Root", "Dispersion:", "0.0100002s"],
    ["ReferenceId:", "0x564D5450", "(source", "IP:", "", "86.77.84.80)"],
    ["Last", "Successful", "Sync", "Time:", "9/15/2025", "12:01:31", "AM"],
    ["Source:", "VM", "IC", "Time", "Synchronization", "Provider"],
    ["Poll", "Interval:", "6", "(64s)"],
    ["Phase", "Offset:", "0.0000869s"],
    ["ClockRate:", "0.0156249s"],
    ["State", "Machine:", "2", "(Sync)"],
    ["Time", "Source", "Flags:", "3", "(Authenticated", "Hardware", ")"],
    ["Server", "Role:", "0", "(None)"],
    ["Last", "Sync", "Error:", "0", "(The", "command", "completed", "successfully.)"],
    ["Time", "since", "Last", "Good", "Sync", "Time:", "19.4823644s"],
]

EN_UNSYNCED = [
    ["Leap", "Indicator:", "3(not", "synchronized)"],
    ["Stratum:", "0", "(unspecified)"],
    ["Precision:", "-23", "(119.209ns", "per", "tick)"],
    ["Root", "Delay:", "0.0000000s"],
    ["Root", "Dispersion:", "0.0000000s"],
    ["ReferenceId:", "0x00000000", "(unspecified)"],
    ["Last", "Successful", "Sync", "Time:", "unspecified"],
    ["Source:", "Local", "CMOS", "Clock"],
    ["Poll", "Interval:", "6", "(64s)"],
    ["Phase", "Offset:", "0.0000000s"],
    ["ClockRate:", "0.0156250s"],
    ["State", "Machine:", "0", "(Unset)"],
    ["Time", "Source", "Flags:", "0", "(None)"],
    ["Server", "Role:", "0", "(None)"],
    [
        "Last",
        "Sync",
        "Error:",
        "1",
        "(The",
        "computer",
        "did",
        "not",
        "resync",
        "because",
        "no",
        "time",
        "data",
        "was",
        "available.)",
    ],
    ["Time", "since", "Last", "Good", "Sync", "Time:", "0.4332958s"],
]

ZH_GOOD_SYNC = [
    ["Leap", "指示符:", "0(无警告)"],
    ["层次:", "2", "(次引用", "-", "与(S)NTP", "同步)"],
    ["精度:", "-6", "(每刻度", "15.625ms)"],
    ["根延迟:", "0.0092768s"],
    ["根分散:", "8.2606345s"],
    ["引用", "ID:", "0x81861B7B", "(源", "IP:", "", "129.134.27.123)"],
    ["上次成功同步时间:", "2025/9/14", "23:55:21"],
    ["源:", "time.facebook.com"],
    ["轮询间隔:", "6", "(64s)"],
    ["相位偏移:", "0.0000012s"],
    ["ClockRate:", "0.0156250s"],
    ["计算机状态:", "2", "(同步)"],
    ["时间源标志:0", "(无)"],
    ["服务器角色:", "0", "(无)"],
    ["上次同步错误:", "0", "(成功地执行了命令。)"],
    ["上次成功同步时间后的时间:", "13.4795503s"],
]

FR_GOOD_SYNC = [
    ["Indicateur", "de", "dérive :", "0(Aucun", "avertissement)"],
    ["Couche :", "4", "(Référence", "secondaire,", "synchronisée", "par", "(S)NTP)"],
    ["Précision :", "-23", "(119.209ns", "par", "battement)"],
    ["Délai", "de", "racine :", "0.1303487s"],
    ["Dispersion", "de", "racine :", "0.0100002s"],
    ["ID", "de", "référence :", "0x564D5450", "(IP", "de", "la", "source :", "", "86.77.84.80)"],
    ["Heure", "de", "la", "dernière", "synchronisation", "réussie :", "15/09/2025", "01:11:10"],
    ["Source :", "VM", "IC", "Time", "Synchronization", "Provider"],
    ["Intervalle", "d’interrogation :", "6", "(64s)"],
    ["Décalage", "de", "phase :", "0.0015321s"],
    ["Fréquence", "d’horloge :", "0.0156249s"],
    ["Ordinateur", "d’état :", "1", "(Attente)"],
    ["Indicateur", "de", "source", "de", "temps :", "3", "(Authentifié", "Matériel", ")"],
    ["Rôle", "de", "serveur :", "0", "(Aucun)"],
    [
        "Erreur",
        "lors",
        "de",
        "la",
        "dernière",
        "synchronisation :",
        "0",
        "(La",
        "commande",
        "s’est",
        "terminée",
        "correctement.)",
    ],
    [
        "Durée",
        "écoulée",
        "depuis",
        "l’heure",
        "de",
        "la",
        "dernière",
        "synchronisation",
        "réussie :",
        "22.0930147s",
    ],
]

DE_LINE_WRAP = [
    ["Sprungindikator:", "0(keine", "Warnung)"],
    ["Stratum:", "3", "(Sekund\\x84rreferenz", "-", "synchr.", "\\x81ber", "(S)NTP)"],
    ["Pr\\x84zision:", "-23", "(119.209ns", "pro", "Tick)"],
    ["Stammverz\\x94gerung:", "0.0336332s"],
    ["Stammabweichung:", "0.1054265s"],
    ["Referenz-ID:", "0xAC689AB6", "(Quell-IP:", "", "172.104.154.182)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "15.09.2025", "13:12:56"],
    ["Quelle:", "de.pool.ntp.org"],
    ["Abrufintervall:", "13", "(8192s)"],
    ["Phasendifferenz:", "-0.0003717s"],
    ["Taktfrequenz:", "0.0156249s"],
    ["Statuscomputer:", "2", "(Sync)"],
    ["Zeitquellenkennzeichen:", "0", "(Keine)"],
    ["Serverrolle:", "0", "(Keine)"],
    [
        "Letzter",
        "Synchronierungsfehler:",
        "2",
        "(Der",
        "Computer",
        "wurde",
        "nicht",
        "synchronisiert,",
        "da",
        "nur",
        "veraltete",
        "Zeitdaten",
    ],
    ["verf\\x81gbar", "waren.)"],
    [
        "Zeit",
        "seit",
        "der",
        "letzten",
        "erfolgr.",
        "Synchronisierungszeit:",
        "4812.7981071s",
    ],
]

# Example with output when w32time is not running / misconfigured
# <<<w32time_status>>>
# Windows time service is not running
NO_WIN32TIME = [
    ["Error: Windows time service is not running"],
]

NEVER_SYNCED = [
    ["Leap", "Indicator:", "3(not", "synchronized)"],
    ["Stratum:", "0", "(unspecified)"],
    ["Precision:", "-23", "(119.209ns", "per", "tick)"],
    ["Root", "Delay:", "0.0000000s"],
    ["Root", "Dispersion:", "0.0000000s"],
    ["ReferenceId:", "0x00000000", "(unspecified)"],
    ["Last", "Successful", "Sync", "Time:", "unspecified"],
    ["Source:", "Local", "CMOS", "Clock"],
    ["Poll", "Interval:", "6", "(64s)"],
    ["Phase", "Offset:", "0.0000000s"],
    ["ClockRate:", "0.0156250s"],
    ["State", "Machine:", "0", "(Unset)"],
    ["Time", "Source", "Flags:", "0", "(None)"],
    ["Server", "Role:", "0", "(None)"],
    [
        "Last",
        "Sync",
        "Error:",
        "1",
        "(The",
        "computer",
        "did",
        "not",
        "resync",
        "because",
        "no",
        "time",
        "data",
        "was",
        "available.)",
    ],
    ["Time", "since", "Last", "Good", "Sync", "Time:", "0.4332958s"],
]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            EN_GOOD_SYNC,
            w32time_status.QueryStatus(
                leap_indicator=0,
                stratum=4,
                precision=-23,
                root_delay=7.58e-05,
                root_dispersion=0.0100002,
                reference_id=1447908432,
                last_successful_sync_time="9/15/2025 12:01:31 AM",
                source="VM IC Time Synchronization Provider",
                poll_interval=64,
                phase_offset=8.69e-05,
                clock_rate=0.0156249,
                state_machine=2,
                time_source_flags=3,
                server_role=0,
                last_sync_error=0,
                seconds_since_last_good_sync=19.4823644,
            ),
        ),
        (
            EN_UNSYNCED,
            w32time_status.QueryStatus(
                leap_indicator=3,
                stratum=0,
                precision=-23,
                root_delay=0.0,
                root_dispersion=0.0,
                reference_id=0,
                last_successful_sync_time="unspecified",
                source="Local CMOS Clock",
                poll_interval=64,
                phase_offset=0.0,
                clock_rate=0.015625,
                state_machine=0,
                time_source_flags=0,
                server_role=0,
                last_sync_error=1,
                seconds_since_last_good_sync=0.4332958,
            ),
        ),
        (
            ZH_GOOD_SYNC,
            w32time_status.QueryStatus(
                leap_indicator=0,
                stratum=2,
                precision=-6,
                root_delay=0.0092768,
                root_dispersion=8.2606345,
                reference_id=2173049723,
                last_successful_sync_time="2025/9/14 23:55:21",
                source="time.facebook.com",
                poll_interval=64,
                phase_offset=1.2e-06,
                clock_rate=0.015625,
                state_machine=2,
                time_source_flags=0,
                server_role=0,
                last_sync_error=0,
                seconds_since_last_good_sync=13.4795503,
            ),
        ),
        (
            FR_GOOD_SYNC,
            w32time_status.QueryStatus(
                leap_indicator=0,
                stratum=4,
                precision=-23,
                root_delay=0.1303487,
                root_dispersion=0.0100002,
                reference_id=1447908432,
                last_successful_sync_time="15/09/2025 01:11:10",
                source="VM IC Time Synchronization Provider",
                poll_interval=64,
                phase_offset=0.0015321,
                clock_rate=0.0156249,
                state_machine=1,
                time_source_flags=3,
                server_role=0,
                last_sync_error=0,
                seconds_since_last_good_sync=22.0930147,
            ),
        ),
        (
            DE_LINE_WRAP,
            w32time_status.QueryStatus(
                leap_indicator=0,
                stratum=3,
                precision=-23,
                root_delay=0.0336332,
                root_dispersion=0.1054265,
                reference_id=2892536502,
                last_successful_sync_time="15.09.2025 13:12:56",
                source="de.pool.ntp.org",
                poll_interval=8192,
                phase_offset=-0.0003717,
                clock_rate=0.0156249,
                state_machine=2,
                time_source_flags=0,
                server_role=0,
                last_sync_error=2,
                seconds_since_last_good_sync=4812.7981071,
            ),
        ),
        (
            NEVER_SYNCED,
            w32time_status.QueryStatus(
                leap_indicator=3,
                stratum=0,
                precision=-23,
                root_delay=0.0,
                root_dispersion=0.0,
                reference_id=0,
                last_successful_sync_time="unspecified",
                source="Local CMOS Clock",
                poll_interval=64,
                phase_offset=0.0,
                clock_rate=0.015625,
                state_machine=0,
                time_source_flags=0,
                server_role=0,
                last_sync_error=1,
                seconds_since_last_good_sync=0.4332958,
            ),
        ),
    ],
)
def test_parse_w32time_status(
    string_table: StringTable, expected: w32time_status.QueryStatus
) -> None:
    assert w32time_status.parse_w32time_status(string_table) == expected


@pytest.mark.parametrize(
    "states, last_sync_error, expected",
    [
        pytest.param(
            {"stale_data": int(State.CRIT)},
            2,
            State.CRIT,
            id="stale_data set to crit",
        ),
        pytest.param(
            {"no_data": int(State.CRIT)},
            2,
            State.WARN,
            id="stale_data not set, but something else set",
        ),
        pytest.param(
            {"no_data": int(State.WARN)},
            1,
            State.WARN,
            id="no_data set to warn",
        ),
        pytest.param(
            {"time_diff_too_large": int(State.WARN)},
            3,
            State.WARN,
            id="time_diff_too_large set to warn",
        ),
        pytest.param(
            {"shutting_down": int(State.CRIT)},
            4,
            State.CRIT,
            id="shutting_down set to crit",
        ),
    ],
)
def test_check_w32time_status_respects_sync_error_states(
    states: w32time_status.StateParams,
    last_sync_error: int,
    expected: State,
) -> None:
    params = deepcopy(w32time_status.DEFAULT_PARAMS)
    params["states"].update(states)
    qs = w32time_status.QueryStatus(
        leap_indicator=0,
        stratum=3,
        precision=-23,
        root_delay=0.0336332,
        root_dispersion=0.1054265,
        reference_id=2892536502,
        last_successful_sync_time="15.09.2025 13:12:56",
        source="de.pool.ntp.org",
        poll_interval=8192,
        phase_offset=-0.0003717,
        clock_rate=0.0156249,
        state_machine=2,
        time_source_flags=0,
        server_role=0,
        last_sync_error=last_sync_error,
        seconds_since_last_good_sync=4812.7981071,
    )
    result = list(w32time_status.check_plugin_w32time_status.check_function(params, qs))
    assert isinstance(result[-1], Result)  # mypy

    assert result[-1].state == expected


def test_check_w32time_status_respects_params() -> None:
    qs = w32time_status.QueryStatus(
        leap_indicator=0,
        stratum=3,
        precision=-23,
        root_delay=0.0336332,
        root_dispersion=0.1054265,
        reference_id=2892536502,
        last_successful_sync_time="15.09.2025 13:12:56",
        source="de.pool.ntp.org",
        poll_interval=8192,
        phase_offset=-0.3717,
        clock_rate=0.0156249,
        state_machine=2,
        time_source_flags=0,
        server_role=0,
        last_sync_error=2,
        seconds_since_last_good_sync=4812.7981071,
    )
    params = {
        "stratum": ("fixed", (2, 5)),
        "offset": ("fixed", (0.2, 0.3)),
        "time_since_last_successful_sync": ("fixed", (1800.0, 2200.0)),
        "states": {"stale_data": State.WARN},
    }
    expected = [
        Result(
            state=State.CRIT,
            summary="Offset: -372 milliseconds (warn/crit below -200 milliseconds/-300 milliseconds)",
        ),
        Metric("time_offset", -0.3717, levels=(0.2, 0.3)),
        Result(
            state=State.CRIT,
            summary="Last successful sync: 1 hour 20 minutes ago (warn/crit at 30 minutes 0 seconds ago/36 minutes 40 seconds ago)",
        ),
        Result(state=State.OK, summary="Source: de.pool.ntp.org"),
        Result(state=State.OK, notice="Root dispersion: 105 milliseconds"),
        Metric("root_dispersion", 0.1054265),
        Result(state=State.OK, notice="Root delay: 34 milliseconds"),
        Metric("root_delay", 0.0336332),
        Result(state=State.WARN, notice="Stratum: 3 (warn/crit at 2/5)"),
        Result(state=State.WARN, notice="Sync status: Stale data received from time provider"),
    ]

    assert list(w32time_status.check_plugin_w32time_status.check_function(params, qs)) == expected


def test_check_w32time_status_never_synced() -> None:
    qs = w32time_status.parse_w32time_status(NEVER_SYNCED)
    params = {
        "states": {"never_synced": State.CRIT},
    }
    expected = [
        Result(
            state=State.CRIT,
            summary="Never synchronized (w32tm reported reference ID and state machine both 0)",
        ),
    ]
    assert list(w32time_status.check_plugin_w32time_status.check_function(params, qs)) == expected


def test_check_w32time_status_no_win32time() -> None:
    qs = w32time_status.parse_w32time_status(NO_WIN32TIME)
    expected = [
        Result(
            state=State.WARN,
            summary="Windows time service is not running",
        ),
    ]
    assert (
        list(w32time_status.check_plugin_w32time_status.check_function(DEFAULT_PARAMS, qs))
        == expected
    )
