#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = "msexch_database"

info = [
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

discovery = {
    "": [("edgetransport/transport-e-mail-datenbank", None), ("information store/_total", None)]
}

checks = {
    "": [
        (
            "edgetransport/transport-e-mail-datenbank",
            {
                "read_recovery_latency": (150.0, 200.0),
                "write_latency": (40.0, 50.0),
                "read_attached_latency": (200.0, 250.0),
                "log_latency": (5.0, 10.0),
            },
            [
                (
                    0,
                    "0.0ms db read (attached) latency",
                    [("db_read_latency", 0.0, 200, 250, None, None)],
                ),
                (
                    0,
                    "0.0ms db read (recovery) latency",
                    [("db_read_recovery_latency", 0.0, 150, 200, None, None)],
                ),
                (
                    0,
                    "0.5ms db write (attached) latency",
                    [("db_write_latency", 0.5, 40, 50, None, None)],
                ),
                (0, "0.0ms Log latency", [("db_log_latency", 0.0, 5, 10, None, None)]),
            ],
        ),
        (
            "information store/_total",
            {
                "read_recovery_latency": (150.0, 200.0),
                "write_latency": (40.0, 50.0),
                "read_attached_latency": (200.0, 250.0),
                "log_latency": (5.0, 10.0),
            },
            [
                (
                    0,
                    "9.0ms db read (attached) latency",
                    [("db_read_latency", 9.0, 200, 250, None, None)],
                ),
                (
                    0,
                    "0.8ms db read (recovery) latency",
                    [("db_read_recovery_latency", 0.8, 150, 200, None, None)],
                ),
                (
                    0,
                    "0.0ms db write (attached) latency",
                    [("db_write_latency", 0.0, 40, 50, None, None)],
                ),
                (
                    0,
                    "0.5ms Log latency",
                    [("db_log_latency", 0.545454545454545, 5, 10, None, None)],
                ),
            ],
        ),
    ]
}
