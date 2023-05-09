#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'msexch_database'

info = [
    [u'locale', u' de-DE'],
    [u'Get-Counter : Die Daten in einer der Leistungsindikator-Stichproben sind'],
    [u'ung\x81ltig. \x9aberpr\x81fen Sie f\x81r jedes PerformanceCounterSample-Objekt, ob die'],
    [u'Status-Eigenschaft g\x81ltige Daten enth\x84lt.'],
    [u'In C:\\Program Files (x86)\\check_mk\\plugins\\msexch_database.ps1:12 Zeichen:1'],
    [u'+ Get-Counter -Counter $counter_name | % {$_.CounterSamples} | Select'],
    [u'path,cookedv ...'], [u'+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'],
    [u'+ CategoryInfo          : InvalidResult: (:) [Get-Counter], Exception'],
    [u'+ FullyQualifiedErrorId : CounterApiError,Microsoft.PowerShell.Commands.Ge'],
    [u'tCounterCommand'], [u'"Path"', u'"CookedValue"'],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (angef\x81gt)"',
        u'"9"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankleseoperationen (wiederherstellung)/sek."',
        u'"5,03606121997173"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (wiederherstellung)"',
        u'"0,8"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankleseoperationen/sek."',
        u'"7,05048570796042"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen"',
        u'"3,14285714285714"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: protokollleseoperationen/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r protokollleseoperationen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankschreiboperationen (angef\x81gt)/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (angef\x81gt)"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankschreiboperationen (wiederherstellung)/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (wiederherstellung)"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: datenbankschreiboperationen/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: leerungszuordnungs-schreibvorg\x84nge/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r leerungszuordnungs-schreibvorg\x84nge"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: protokollschreiboperationen/sek"',
        u'"11,0793346839378"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\e/a: durchschnittliche wartezeit f\x81r protokollschreiboperationen"',
        u'"0,545454545454545"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(information store/_total)\\mittlere wartezeit bei datenbank-cachefehlern (anh\x84ngend)"',
        u'"8,5"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\defragmentierungstasks"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\defragmentierungstasks: ausstehende"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\sitzungen in verwendung"',
        u'"11"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\sitzungen % in verwendung"',
        u'"1,02899906454631"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: % cachetreffer"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: cachetreffer/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: cachefehlschl\x84ge/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle \x94ffnen: operationen/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\tabelle schlie\xe1en: operationen/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\ge\x94ffnete tabellen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokoll: schreiben byte/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokoll: generierte bytes/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\wartende protokollthreads"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\pr\x81fpunkttiefe f\x81r protokollgenerierung"',
        u'"2"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokollgenerierung: ideale pr\x81fpunkttiefe"',
        u'"77"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokollpr\x81fpunkttiefe: als % der zieltiefe"',
        u'"2,5974025974026"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\max. pr\x81fpunkttiefe f\x81r protokollgenerierung"',
        u'"1024"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\verlustausfalltiefe f\x81r protokollgenerierung"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\generierte protokolldateien"',
        u'"8411"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\vorzeitig generierte protokolldateien"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\aktuelle protokolldateigenerierung"',
        u'"169698"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokollschreiboperationen/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\protokolldatensatzverz\x94gerungen/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\zugewiesene version-buckets"',
        u'"1"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbank: cachegr\x94\xe1e (mb)"',
        u'"37"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache: fehlschl\x84ge/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache % treffer"',
        u'"100"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache % treffer (eindeutig)"',
        u'"100"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache: anforderungen/sek. (eindeutig)"',
        u'"1,00721224399435"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankcache: anforderungen/sek."',
        u'"4,02884897597738"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\streamingsicherung: gelesene seiten/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankwartung: dauer seit letzter"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\datenbankwartung: fehlerhafte seitenpr\x81fsummen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankleseoperationen (angef\x81gt)/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (angef\x81gt)"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankleseoperationen (wiederherstellung)/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (wiederherstellung)"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankleseoperationen/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: protokollleseoperationen/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r protokollleseoperationen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankschreiboperationen (angef\x81gt)/sek."',
        u'"2,01442448798869"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (angef\x81gt)"',
        u'"0,5"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankschreiboperationen (wiederherstellung)/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (wiederherstellung)"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: datenbankschreiboperationen/sek."',
        u'"2,01442448798869"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen"',
        u'"0,5"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: leerungszuordnungs-schreibvorg\x84nge/sek."',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r leerungszuordnungs-schreibvorg\x84nge"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: protokollschreiboperationen/sek"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\e/a: durchschnittliche wartezeit f\x81r protokollschreiboperationen"',
        u'"0"'
    ],
    [
        u'"\\\\sv083\\msexchange-datenbank  ==> instanzen(edgetransport/transport-e-mail-datenbank)\\mittlere wartezeit bei datenbank-cachefehlern (anh\x84ngend)"',
        u'"0"'
    ]
]

discovery = {
    '': [(u'edgetransport/transport-e-mail-datenbank', None), (u'information store/_total', None)]
}

checks = {
    '': [(u'edgetransport/transport-e-mail-datenbank', {
        'read_recovery_latency': (150.0, 200.0),
        'write_latency': (40.0, 50.0),
        'read_attached_latency': (200.0, 250.0),
        'log_latency': (5.0, 10.0)
    }, [(0, '0.0ms db read (attached) latency', [('db_read_latency', 0.0, 200, 250, None, None)]),
        (0, '0.0ms db read (recovery) latency', [('db_read_recovery_latency', 0.0, 150, 200, None,
                                                  None)]),
        (0, '0.5ms db write (attached) latency', [('db_write_latency', 0.5, 40, 50, None, None)]),
        (0, '0.0ms Log latency', [('db_log_latency', 0.0, 5, 10, None, None)])]),
         (u'information store/_total', {
             'read_recovery_latency': (150.0, 200.0),
             'write_latency': (40.0, 50.0),
             'read_attached_latency': (200.0, 250.0),
             'log_latency': (5.0, 10.0)
         }, [(0, '9.0ms db read (attached) latency', [('db_read_latency', 9.0, 200, 250, None,
                                                       None)]),
             (0, '0.8ms db read (recovery) latency', [('db_read_recovery_latency', 0.8, 150, 200,
                                                       None, None)]),
             (0, '0.0ms db write (attached) latency', [('db_write_latency', 0.0, 40, 50, None,
                                                        None)]),
             (0, '0.5ms Log latency', [('db_log_latency', 0.545454545454545, 5, 10, None, None)])])]
}
