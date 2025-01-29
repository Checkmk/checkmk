#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.msexch.agent_based.msexch_database import (
    check_msexch_database,
    inventory_msexch_database,
    Params,
    parse_msexch_database,
)

_DE_AGENT_OUTPUT = [
    ["locale", " de-DE"],
    ["Get-Counter : Die Daten in einer der Leistungsindikator-Stichproben sind"],
    ["ung\x81ltig. \x9aberpr\x81fen Sie f\x81r jedes PerformanceCounterSample-Objekt, ob die"],
    ["Status-Eigenschaft g\x81ltige Daten enth\x84lt."],
    ["In C:\\Program Files (x86)\\check_mk\\plugins\\msexch_database.ps1:12 Zeichen:1"],
    ["+ Get-Counter -Counter $counter_name | % {$_.CounterSamples} | Select"],
    ["path,cookedv ..."],
    ["+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"],
    ["+ CategoryInfo          : InvalidResult: (:) [Get-Counter], Exception"],
    ["+ FullyQualifiedErrorId : CounterApiError,Microsoft.PowerShell.Commands.Ge"],
    ["tCounterCommand"],
    ['"Path"', '"CookedValue"'],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (angef\x81gt)"',
        '"9"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankleseoperationen (wiederherstellung)/sek."',
        '"5,03606121997173"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (wiederherstellung)"',
        '"0,8"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankleseoperationen/sek."',
        '"7,05048570796042"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen"',
        '"3,14285714285714"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: protokollleseoperationen/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r protokollleseoperationen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankschreiboperationen (angef\x81gt)/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (angef\x81gt)"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankschreiboperationen (wiederherstellung)/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (wiederherstellung)"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankschreiboperationen/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: leerungszuordnungs-schreibvorg\x84nge/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r leerungszuordnungs-schreibvorg\x84nge"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: protokollschreiboperationen/sek"',
        '"11,0793346839378"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r protokollschreiboperationen"',
        '"0,545454545454545"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\mittlere wartezeit bei datenbank-cachefehlern (anh\x84ngend)"',
        '"8,5"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\defragmentierungstasks"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\defragmentierungstasks: ausstehende"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\sitzungen in verwendung"',
        '"11"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\sitzungen % in verwendung"',
        '"1,02899906454631"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: % cachetreffer"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: cachetreffer/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: cachefehlschl\x84ge/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: operationen/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle schlie\xe1en: operationen/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\ge\x94ffnete tabellen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokoll: schreiben byte/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokoll: generierte bytes/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\wartende protokollthreads"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\pr\x81fpunkttiefe f\x81r protokollgenerierung"',
        '"2"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokollgenerierung: ideale pr\x81fpunkttiefe"',
        '"77"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokollpr\x81fpunkttiefe: als % der zieltiefe"',
        '"2,5974025974026"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\max. pr\x81fpunkttiefe f\x81r protokollgenerierung"',
        '"1024"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\verlustausfalltiefe f\x81r protokollgenerierung"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\generierte protokolldateien"',
        '"8411"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\vorzeitig generierte protokolldateien"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\aktuelle protokolldateigenerierung"',
        '"169698"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokollschreiboperationen/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokolldatensatzverz\x94gerungen/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\zugewiesene version-buckets"',
        '"1"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbank: cachegr\x94\xe1e (mb)"',
        '"37"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache: fehlschl\x84ge/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache % treffer"',
        '"100"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache % treffer (eindeutig)"',
        '"100"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache: anforderungen/sek. (eindeutig)"',
        '"1,00721224399435"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache: anforderungen/sek."',
        '"4,02884897597738"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\streamingsicherung: gelesene seiten/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankwartung: dauer seit letzter"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankwartung: fehlerhafte seitenpr\x81fsummen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankleseoperationen (angef\x81gt)/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (angef\x81gt)"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankleseoperationen (wiederherstellung)/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (wiederherstellung)"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankleseoperationen/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: protokollleseoperationen/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r protokollleseoperationen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankschreiboperationen (angef\x81gt)/sek."',
        '"2,01442448798869"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (angef\x81gt)"',
        '"0,5"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankschreiboperationen (wiederherstellung)/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (wiederherstellung)"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankschreiboperationen/sek."',
        '"2,01442448798869"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen"',
        '"0,5"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: leerungszuordnungs-schreibvorg\x84nge/sek."',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r leerungszuordnungs-schreibvorg\x84nge"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: protokollschreiboperationen/sek"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r protokollschreiboperationen"',
        '"0"',
    ],
    [
        '"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\mittlere wartezeit bei datenbank-cachefehlern (anh\x84ngend)"',
        '"0"',
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _DE_AGENT_OUTPUT,
            [
                Service(item="edgetransport/transport-e-mail-datenbank"),
                Service(item="information store/_total"),
            ],
        ),
    ],
)
def test_parse_msexch_database(string_table: StringTable, expected_result: DiscoveryResult) -> None:
    section = parse_msexch_database(string_table)
    assert sorted(inventory_msexch_database(section)) == expected_result


@pytest.mark.parametrize(
    "string_table, item, params, expected_result",
    [
        (
            _DE_AGENT_OUTPUT,
            "edgetransport/transport-e-mail-datenbank",
            Params(
                read_attached_latency_s=("no_levels", None),
                read_recovery_latency_s=("no_levels", None),
                write_latency_s=("no_levels", None),
                log_latency_s=("no_levels", None),
            ),
            [
                Result(state=State.OK, summary="DB read (attached) latency: 0 seconds"),
                Metric("db_read_latency_s", 0.0),
                Result(state=State.OK, summary="DB read (recovery) latency: 0 seconds"),
                Metric("db_read_recovery_latency_s", 0.0),
                Result(state=State.OK, summary="DB write (attached) latency: 500 microseconds"),
                Metric("db_write_latency_s", 0.0005),
                Result(state=State.OK, summary="Log latency: 0 seconds"),
                Metric("db_log_latency_s", 0.0),
            ],
        ),
        (
            _DE_AGENT_OUTPUT,
            "information store/_total",
            Params(
                read_attached_latency_s=("fixed", (0.005, 0.01)),
                read_recovery_latency_s=("fixed", (0.0001, 0.0002)),
                write_latency_s=("no_levels", None),
                log_latency_s=("no_levels", None),
            ),
            [
                Result(
                    state=State.WARN,
                    summary="DB read (attached) latency: 9 milliseconds (warn/crit at 5 milliseconds/10 milliseconds)",
                ),
                Metric("db_read_latency_s", 0.009, levels=(0.005, 0.01)),
                Result(
                    state=State.CRIT,
                    summary="DB read (recovery) latency: 800 microseconds (warn/crit at 100 microseconds/200 microseconds)",
                ),
                Metric("db_read_recovery_latency_s", 0.0008, levels=(0.0001, 0.0002)),
                Result(state=State.OK, summary="DB write (attached) latency: 0 seconds"),
                Metric("db_write_latency_s", 0.0),
                Result(state=State.OK, summary="Log latency: 545 microseconds"),
                Metric("db_log_latency_s", 0.0005454545454545449),
            ],
        ),
    ],
)
def test_check_msexch_database(
    string_table: StringTable,
    item: str,
    params: Params,
    expected_result: CheckResult,
) -> None:
    section = parse_msexch_database(string_table)
    assert list(check_msexch_database(item, params, section)) == expected_result
