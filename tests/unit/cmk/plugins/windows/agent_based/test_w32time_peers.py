#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.windows.agent_based import w32time_peers

DE_PEERS_EXAMPLE_COM = [
    ["Anzahl", "Peers:", "12"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30983.5517802s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30983.6666162s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30983.7917389s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30983.9172860s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.0420428s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.1672281s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.2920495s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.4170905s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.5420717s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.6669730s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.7920216s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
    ["---"],
    ["Peer:", "example.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "30984.9169029s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "15", "(32768s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "(null)"],
    [
        "Letzter",
        "Synchronisierungsfehler:",
        "0x800705B4",
        "(Dieser",
        "Vorgang",
        "wurde",
        "wegen",
        "Zeit\x81berschreitung",
        "zur\x81ckgegeben.",
        ")",
    ],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Aufl\x94sungsversuche:", "0"],
    ["G\x81ltiger", "Datenz\x84hler:", "1"],
    ["Erreichbarkeit:", "2"],
]

EN_PEERS = [
    ["#Peers:", "5"],
    ["---"],
    ["Peer:", "time.facebook.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "1754.9964697s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:50", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "time.google.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "1755.0132055s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:50", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "de.pool.ntp.org"],
    ["State:", "Active"],
    ["Time", "Remaining:", "612.9102195s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "2", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:41:48", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "time.cloudflare.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "618.9722708s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "3", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:41:54", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "example.com"],
    ["State:", "Pending"],
    ["Time", "Remaining:", "5817.0042395s"],
    ["Mode:", "0", "(reserved)"],
    ["Stratum:", "0", "(unspecified)"],
    ["PeerPoll", "Interval:", "0", "(unspecified)"],
    ["HostPoll", "Interval:", "0", "(unspecified)"],
    ["Last", "Successful", "Sync", "Time:", "(null)"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "4"],
    ["ValidDataCounter:", "0"],
    ["Reachability:", "0"],
]

EN_PEERS_STRATUM_1_TO_3 = [
    ["#Peers:", "3"],
    ["---"],
    ["Peer:", "time.facebook.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "1754.9964697s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:50", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "time.cloudflare.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "618.9722708s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "3", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:41:54", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "de.pool.ntp.org"],
    ["State:", "Active"],
    ["Time", "Remaining:", "612.9102195s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "2", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:41:48", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
]

EN_SINGLE_PEER = [
    ["#Peers:", "1"],
    ["---"],
    ["Peer:", "time.facebook.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "1754.9964697s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:50", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
]

# One peer fails on stratum, another on reachability — tests that universal
# suppression works the same regardless of which check type triggers the failure.
EN_MIXED_FAILURES = [
    ["#Peers:", "3"],
    ["---"],
    ["Peer:", "stratum-bad.example.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "100.0s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "4", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:00", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "reachability-bad.example.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "200.0s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "(null)"],
    [
        "LastSyncError:",
        "0x800705B4",
        "(This",
        "operation",
        "returned",
        "because",
        "the",
        "timeout",
        "period",
        "expired.",
        ")",
    ],
    ["LastSyncErrorMsgId:", "0x0000005C", "(The", "peer", "is", "unreachable.", ")"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "4"],
    ["Reachability:", "168"],  # 0b10101000: 5 total failures, 3 consecutive
    ["---"],
    ["Peer:", "good.example.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "300.0s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "2", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:00:00", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
]

EN_WITH_EXTRA_LINE = [
    ["#Peers:", "2"],
    ["---"],
    ["Peer:", "time.google.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "1755.0132055s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:50", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "de.pool.ntp.org"],
    ["State:", "Active"],
    ["Time", "Remaining:", "612.9102195s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "2", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["OH", "NO:", "AN", "EXTRA", "LINE", "NOW", "WHAT?"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:41:48", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
]

EN_WITH_REMOVED_LINE = [
    ["#Peers:", "2"],
    ["---"],
    ["Peer:", "time.google.com"],
    ["State:", "Active"],
    ["Time", "Remaining:", "1755.0132055s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "7:00:50", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
    ["---"],
    ["Peer:", "de.pool.ntp.org"],
    ["State:", "Active"],
    ["Time", "Remaining:", "612.9102195s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "2", "(secondary", "reference", "-", "syncd", "by", "(S)NTP)"],
    ["PeerPoll", "Interval:", "12", "(4096s)"],
    # ["HostPoll", "Interval:", "12", "(4096s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "6:41:48", "PM"],
    ["LastSyncError:", "0x00000000", "(Succeeded)"],
    ["LastSyncErrorMsgId:", "0x00000000", "(Succeeded)"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "8"],
    ["Reachability:", "255"],
]

EN_WITH_ERROR = [
    ["#Peers:", "16"],
    ["---"],
    ["Peer:", "de.pool.ntp.org"],
    ["State:", "Active"],
    ["Time", "Remaining:", "12.3386152s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "10", "(1024s)"],
    ["HostPoll", "Interval:", "5", "(32s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "10:08:35", "AM"],
    [
        "LastSyncError:",
        "0x800705B4",
        "(This",
        "operation",
        "returned",
        "because",
        "the",
        "timeout",
        "period",
        "expired.",
        ")",
    ],
    ["LastSyncErrorMsgId:", "0x0000005C", "(The", "peer", "is", "unreachable.", ")"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "0"],
    ["ValidDataCounter:", "0"],
    ["Reachability:", "168"],
]

EN_WITH_0_REACHABILITY_AND_HIGH_RESOLVE_ATTEMPTS = [
    ["#Peers:", "16"],
    ["---"],
    ["Peer:", "de.pool.ntp.org"],
    ["State:", "Active"],
    ["Time", "Remaining:", "12.3386152s"],
    ["Mode:", "3", "(Client)"],
    ["Stratum:", "1", "(primary", "reference", "-", "syncd", "by", "radio", "clock)"],
    ["PeerPoll", "Interval:", "10", "(1024s)"],
    ["HostPoll", "Interval:", "5", "(32s)"],
    ["Last", "Successful", "Sync", "Time:", "9/18/2025", "10:08:35", "AM"],
    [
        "LastSyncError:",
        "0x800705B4",
        "(This",
        "operation",
        "returned",
        "because",
        "the",
        "timeout",
        "period",
        "expired.",
        ")",
    ],
    ["LastSyncErrorMsgId:", "0x0000005C", "(The", "peer", "is", "unreachable.", ")"],
    ["AuthTypeMsgId:", "0x0000005A", "(NoAuth", ")"],
    ["Resolve", "Attempts:", "3"],
    ["ValidDataCounter:", "0"],
    ["Reachability:", "0"],
]

DE_MISSING_PEER_NAME = [
    ["Anzahl", "Peers:", "1"],
    ["---"],
    ["Peer:", ""],
    ["Status:", "Ausstehend"],
    ["Verbleibende", "Zeit:", "660.8019897s"],
    ["Modus:", "0", "(Reserviert)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "04.03.2026", "14:12:09"],
    ["Letzter", "Synchronisierungsfehler:", "0x00000000", "(Erfolgreich)"],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Auflâsungsversuche:", "0"],
    ["GÂltiger", "Datenzâhler:", "0"],
    ["Erreichbarkeit:", "0"],
]


# We have never seen this in practice, we don't know if it's possible
# but we handle it, in case.
DE_MULTIPLE_MISSING_PEER_NAMES = [
    ["Anzahl", "Peers:", "2"],
    ["---"],
    ["Peer:", ""],
    ["Status:", "Ausstehend"],
    ["Verbleibende", "Zeit:", "660.8019897s"],
    ["Modus:", "0", "(Reserviert)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "04.03.2026", "14:12:09"],
    ["Letzter", "Synchronisierungsfehler:", "0x00000000", "(Erfolgreich)"],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Auflâsungsversuche:", "0"],
    ["GÂltiger", "Datenzâhler:", "0"],
    ["Erreichbarkeit:", "0"],
    ["---"],
    ["Peer:", ""],
    ["Status:", "Ausstehend"],
    ["Verbleibende", "Zeit:", "658.8019897s"],
    ["Modus:", "0", "(Reserviert)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "04.03.2026", "14:11:11"],
    ["Letzter", "Synchronisierungsfehler:", "0x00000000", "(Erfolgreich)"],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Auflâsungsversuche:", "0"],
    ["GÂltiger", "Datenzâhler:", "0"],
    ["Erreichbarkeit:", "0"],
]


# We have never seen this in practice, we don't know if it's possible
# but we handle it, in case.
# Missing name + Normal peer
DE_MIXED_MISSING_PEER_NAME = [
    ["Anzahl", "Peers:", "2"],
    ["---"],
    ["Peer:", ""],
    ["Status:", "Ausstehend"],
    ["Verbleibende", "Zeit:", "660.8019897s"],
    ["Modus:", "0", "(Reserviert)"],
    ["Stratum:", "0", "(nicht", "angegeben)"],
    ["PeerAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["HostAbrufintervall:", "0", "(nicht", "angegeben)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "04.03.2026", "14:12:09"],
    ["Letzter", "Synchronisierungsfehler:", "0x00000000", "(Erfolgreich)"],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Auflâsungsversuche:", "0"],
    ["GÂltiger", "Datenzâhler:", "0"],
    ["Erreichbarkeit:", "0"],
    ["---"],
    ["Peer:", "time.cloudflare.com"],
    ["Status:", "Aktiv"],
    ["Verbleibende", "Zeit:", "3017.0667103s"],
    ["Modus:", "3", "(Client)"],
    ["Stratum:", "3", "(Sekundärreferenz", "-", "synchr.", "über", "(S)NTP)"],
    ["PeerAbrufintervall:", "13", "(8192s)"],
    ["HostAbrufintervall:", "13", "(8192s)"],
    ["Letzte", "erfolgr.", "Synchronisierungszeit:", "07.03.2026", "04:17:06"],
    ["Letzter", "Synchronisierungsfehler:", "0x00000000", "(Erfolgreich)"],
    ["Letzte", "Synchronisierungsfehlermeldungs-ID:", "0x00000000", "(Erfolgreich)"],
    ["Auth-Typnachricht-ID:", "0x0000005A", "(NoAuth", ")"],
    ["Auflösungsversuche:", "0"],
    ["Gültiger", "Datenzähler:", "8"],
    ["Erreichbarkeit:", "255"],
]


NO_PEERS = [["#Peers:", "0"]]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            DE_PEERS_EXAMPLE_COM,
            {
                "example.com": w32time_peers.QueryPeers(
                    peer="example.com",
                    time_remaining=30984.9169029,
                    stratum=0,
                    last_successful_sync_time="(null)",
                    last_sync_error_str="Dieser Vorgang wurde wegen Zeit\x81berschreitung zur\x81ckgegeben.",
                    last_sync_error_msg=None,
                    raw_reachability=2,
                    reachability=w32time_peers.Reachability(
                        total_failures=1, consecutive_failures=1, total_attempts=2
                    ),
                )
            },
        ),
        (
            EN_PEERS,
            {
                "de.pool.ntp.org": w32time_peers.QueryPeers(
                    peer="de.pool.ntp.org",
                    time_remaining=612.9102195,
                    stratum=2,
                    last_successful_sync_time="9/18/2025 6:41:48 PM",
                    last_sync_error_str="Succeeded",
                    last_sync_error_msg=None,
                    raw_reachability=255,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=8
                    ),
                ),
                "example.com": w32time_peers.QueryPeers(
                    peer="example.com",
                    time_remaining=5817.0042395,
                    stratum=0,
                    last_successful_sync_time="(null)",
                    last_sync_error_str="Succeeded",
                    last_sync_error_msg=None,
                    raw_reachability=0,
                    reachability=w32time_peers.Reachability(
                        total_failures=4, consecutive_failures=4, total_attempts=4
                    ),
                ),
                "time.cloudflare.com": w32time_peers.QueryPeers(
                    peer="time.cloudflare.com",
                    time_remaining=618.9722708,
                    stratum=3,
                    last_successful_sync_time="9/18/2025 6:41:54 PM",
                    last_sync_error_str="Succeeded",
                    last_sync_error_msg=None,
                    raw_reachability=255,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=8
                    ),
                ),
                "time.facebook.com": w32time_peers.QueryPeers(
                    peer="time.facebook.com",
                    time_remaining=1754.9964697,
                    stratum=1,
                    last_successful_sync_time="9/18/2025 7:00:50 PM",
                    last_sync_error_str="Succeeded",
                    last_sync_error_msg=None,
                    raw_reachability=255,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=8
                    ),
                ),
                "time.google.com": w32time_peers.QueryPeers(
                    peer="time.google.com",
                    time_remaining=1755.0132055,
                    stratum=1,
                    last_successful_sync_time="9/18/2025 7:00:50 PM",
                    last_sync_error_str="Succeeded",
                    last_sync_error_msg=None,
                    raw_reachability=255,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=8
                    ),
                ),
            },
        ),
        (
            DE_MISSING_PEER_NAME,
            {
                "(unnamed peer 1)": w32time_peers.QueryPeers(
                    peer="",
                    time_remaining=660.8019897,
                    stratum=0,
                    last_successful_sync_time="04.03.2026 14:12:09",
                    last_sync_error_str="Erfolgreich",
                    last_sync_error_msg=None,
                    raw_reachability=0,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=0
                    ),
                )
            },
        ),
        (
            DE_MULTIPLE_MISSING_PEER_NAMES,
            {
                "(unnamed peer 1)": w32time_peers.QueryPeers(
                    peer="",
                    time_remaining=660.8019897,
                    stratum=0,
                    last_successful_sync_time="04.03.2026 14:12:09",
                    last_sync_error_str="Erfolgreich",
                    last_sync_error_msg=None,
                    raw_reachability=0,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=0
                    ),
                ),
                "(unnamed peer 2)": w32time_peers.QueryPeers(
                    peer="",
                    time_remaining=658.8019897,
                    stratum=0,
                    last_successful_sync_time="04.03.2026 14:11:11",
                    last_sync_error_str="Erfolgreich",
                    last_sync_error_msg=None,
                    raw_reachability=0,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=0
                    ),
                ),
            },
        ),
        (
            DE_MIXED_MISSING_PEER_NAME,
            {
                "(unnamed peer 1)": w32time_peers.QueryPeers(
                    peer="",
                    time_remaining=660.8019897,
                    stratum=0,
                    last_successful_sync_time="04.03.2026 14:12:09",
                    last_sync_error_str="Erfolgreich",
                    last_sync_error_msg=None,
                    raw_reachability=0,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=0
                    ),
                ),
                "time.cloudflare.com": w32time_peers.QueryPeers(
                    peer="time.cloudflare.com",
                    time_remaining=3017.0667103,
                    stratum=3,
                    last_successful_sync_time="07.03.2026 04:17:06",
                    last_sync_error_str="Erfolgreich",
                    last_sync_error_msg=None,
                    raw_reachability=255,
                    reachability=w32time_peers.Reachability(
                        total_failures=0, consecutive_failures=0, total_attempts=8
                    ),
                ),
            },
        ),
        (
            NO_PEERS,
            {},
        ),
    ],
)
def test_parse_w32time_peers(
    string_table: StringTable, expected: dict[str, w32time_peers.QueryPeers]
) -> None:
    assert w32time_peers.parse_w32time_peers(string_table) == expected


@pytest.mark.parametrize(
    "string_table,substr",
    [
        (EN_WITH_EXTRA_LINE, "Peer parsed to more than"),
        (EN_WITH_REMOVED_LINE, "Peer parsed to less than"),
    ],
)
def test_parse_w32time_peers_parse_fail(string_table: StringTable, substr: str) -> None:
    with pytest.raises(ValueError, match=substr):
        w32time_peers.parse_w32time_peers(string_table)


@pytest.mark.parametrize(
    "string_table, item, params, expected",
    [
        pytest.param(
            EN_PEERS,
            "time.google.com",
            w32time_peers.DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Next poll in: 29 minutes 15 seconds"),
            ],
            id="green path",
        ),
        pytest.param(
            EN_WITH_ERROR,
            "de.pool.ntp.org",
            w32time_peers.DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Last successful sync time: 9/18/2025 10:08:35 AM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 5"),
                Result(
                    state=State.OK,
                    notice="Consecutive failures (last 8 attempts): 3",
                ),
                Result(state=State.OK, summary="Last sync error: The peer is unreachable."),
                Result(
                    state=State.OK,
                    notice="Details from w32tm: This operation returned because the timeout period expired.",
                ),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Next poll in: 12 seconds"),
            ],
            id="error, default params (no alert)",
        ),
        pytest.param(
            EN_WITH_ERROR,
            "de.pool.ntp.org",
            {
                **w32time_peers.DEFAULT_PARAMS,
                "reachability_consecutive_failures": ("fixed", (2, 3)),
                "reachability_total_failures": ("fixed", (5, 6)),
            },
            [
                Result(state=State.OK, summary="Last successful sync time: 9/18/2025 10:08:35 AM"),
                Result(
                    state=State.WARN,
                    summary="Total failures (last 8 attempts): 5 (warn/crit at 5/6)",
                ),
                Result(
                    state=State.CRIT,
                    summary="Consecutive failures (last 8 attempts): 3 (warn/crit at 2/3)",
                ),
                Result(state=State.OK, summary="Last sync error: The peer is unreachable."),
                Result(
                    state=State.OK,
                    notice="Details from w32tm: This operation returned because the timeout period expired.",
                ),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Next poll in: 12 seconds"),
            ],
            id="error, with alerts",
        ),
        pytest.param(
            EN_PEERS,
            "time.cloudflare.com",
            {
                **w32time_peers.DEFAULT_PARAMS,
                "stratum": ("fixed", (2, 3)),
            },
            [
                Result(state=State.OK, summary="Last successful sync time: 9/18/2025 6:41:54 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.CRIT, summary="Stratum: 3 (warn/crit at 2/3)"),
                Result(state=State.OK, summary="Next poll in: 10 minutes 19 seconds"),
            ],
            id="high stratum, with alerts",
        ),
        pytest.param(
            EN_WITH_0_REACHABILITY_AND_HIGH_RESOLVE_ATTEMPTS,
            "de.pool.ntp.org",
            {
                **w32time_peers.DEFAULT_PARAMS,
                "reachability_total_failures": ("fixed", (2, 3)),
            },
            [
                Result(state=State.OK, summary="Last successful sync time: 9/18/2025 10:08:35 AM"),
                Result(
                    state=State.CRIT,
                    summary="Total failures (3 attempts): 3 (warn/crit at 2/3)",
                ),
                Result(
                    state=State.OK,
                    notice="Consecutive failures (3 attempts): 3",
                ),
                Result(state=State.OK, summary="Last sync error: The peer is unreachable."),
                Result(
                    state=State.OK,
                    notice="Details from w32tm: This operation returned because the timeout period expired.",
                ),
                Result(state=State.OK, summary="Stratum: 1"),
                Result(state=State.OK, summary="Next poll in: 12 seconds"),
            ],
            id="0 reachability, use resolve attempts instead",
        ),
        pytest.param(
            DE_MISSING_PEER_NAME,
            "(unnamed peer 1)",
            w32time_peers.DEFAULT_PARAMS,
            [Result(state=State.WARN, summary="Peer with no name found!")],
            id="1 peer, missing name",
        ),
        pytest.param(
            DE_MIXED_MISSING_PEER_NAME,
            "(unnamed peer 1)",
            w32time_peers.DEFAULT_PARAMS,
            [Result(state=State.WARN, summary="Peer with no name found!")],
            id="2 peers, 1 is missing name and warns",
        ),
        pytest.param(
            DE_MIXED_MISSING_PEER_NAME,
            "time.cloudflare.com",
            w32time_peers.DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Last successful sync time: 07.03.2026 04:17:06"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, summary="Stratum: 3"),
                Result(state=State.OK, summary="Next poll in: 50 minutes 17 seconds"),
            ],
            id="2 peers, 1 is missing name, other is OK",
        ),
    ],
)
def test_check_w32time_peers(
    string_table: StringTable, item: str, params: w32time_peers.Params, expected: CheckResult
) -> None:
    parsed = w32time_peers.parse_w32time_peers(string_table)
    result = list(w32time_peers.check_w32time_peers(item, params, parsed))
    assert result == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            EN_PEERS,
            [
                Service(item="time.facebook.com"),
                Service(item="time.google.com"),
                Service(item="de.pool.ntp.org"),
                Service(item="time.cloudflare.com"),
            ],
        ),
        (DE_PEERS_EXAMPLE_COM, []),
        (DE_MISSING_PEER_NAME, [Service(item="(unnamed peer 1)")]),
        (
            DE_MULTIPLE_MISSING_PEER_NAMES,
            [
                Service(item="(unnamed peer 1)"),
                Service(item="(unnamed peer 2)"),
            ],
        ),
        (
            DE_MIXED_MISSING_PEER_NAME,
            [
                Service(item="(unnamed peer 1)"),
                Service(item="time.cloudflare.com"),
            ],
        ),
        (NO_PEERS, []),
    ],
)
def test_discover_w32time_peers(string_table: StringTable, expected: DiscoveryResult) -> None:
    parsed = w32time_peers.parse_w32time_peers(string_table)

    result = list(w32time_peers.discover_w32time_peers({"mode": "single"}, parsed))
    assert result == expected

    result = list(w32time_peers.discover_w32time_peers({"mode": "both"}, parsed))
    assert result == expected

    result = list(w32time_peers.discover_w32time_peers({"mode": "summary"}, parsed))
    assert result == []

    result = list(w32time_peers.discover_w32time_peers({"mode": "neither"}, parsed))
    assert result == []


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            EN_PEERS,
            [Service()],
        ),
        (DE_PEERS_EXAMPLE_COM, [Service()]),
        (NO_PEERS, []),
    ],
)
def test_discover_w32time_peers_summary(
    string_table: StringTable, expected: DiscoveryResult
) -> None:
    parsed = w32time_peers.parse_w32time_peers(string_table)

    result = list(w32time_peers.discover_w32time_peers_summary({"mode": "single"}, parsed))
    assert result == []

    result = list(w32time_peers.discover_w32time_peers_summary({"mode": "neither"}, parsed))
    assert result == []

    result = list(w32time_peers.discover_w32time_peers_summary({"mode": "summary"}, parsed))
    assert result == expected

    result = list(w32time_peers.discover_w32time_peers_summary({"mode": "both"}, parsed))
    assert result == expected


@pytest.mark.parametrize(
    "stratum_levels, universal, expected",
    [
        pytest.param(
            (1, 20),
            True,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 3"),
                Result(state=State.OK, notice="\nPeer: time.facebook.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.WARN,
                    summary="time.facebook.com: Stratum: 1 (warn/crit at 1/20)",
                    details="Stratum: 1 (warn/crit at 1/20)",
                ),
                Result(state=State.OK, notice="Next poll in: 29 minutes 15 seconds"),
                Result(state=State.OK, notice="\nPeer: time.cloudflare.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:54 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.WARN,
                    summary="time.cloudflare.com: Stratum: 3 (warn/crit at 1/20)",
                    details="Stratum: 3 (warn/crit at 1/20)",
                ),
                Result(state=State.OK, notice="Next poll in: 10 minutes 19 seconds"),
                Result(state=State.OK, notice="\nPeer: de.pool.ntp.org"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:48 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.WARN,
                    summary="de.pool.ntp.org: Stratum: 2 (warn/crit at 1/20)",
                    details="Stratum: 2 (warn/crit at 1/20)",
                ),
                Result(state=State.OK, notice="Next poll in: 10 minutes 13 seconds"),
            ],
            id="all peers warn => overall warn",
        ),
        pytest.param(
            (3, 4),
            True,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 1 (alerts suppressed)"),
                Result(state=State.OK, notice="\nPeer: time.facebook.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 1"),
                Result(state=State.OK, notice="Next poll in: 29 minutes 15 seconds"),
                Result(state=State.OK, notice="\nPeer: time.cloudflare.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:54 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.OK,
                    notice="Stratum: 3 (warn/crit at 3/4) (alerts suppressed)",
                ),
                Result(state=State.OK, notice="Next poll in: 10 minutes 19 seconds"),
                Result(state=State.OK, notice="\nPeer: de.pool.ntp.org"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:48 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 2"),
                Result(state=State.OK, notice="Next poll in: 10 minutes 13 seconds"),
            ],
            id="levels set to 3/4, all must fail => overall ok",
        ),
        pytest.param(
            (3, 4),
            False,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 1"),
                Result(state=State.OK, notice="\nPeer: time.facebook.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 1"),
                Result(state=State.OK, notice="Next poll in: 29 minutes 15 seconds"),
                Result(state=State.OK, notice="\nPeer: time.cloudflare.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:54 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.WARN,
                    summary="time.cloudflare.com: Stratum: 3 (warn/crit at 3/4)",
                    details="Stratum: 3 (warn/crit at 3/4)",
                ),
                Result(state=State.OK, notice="Next poll in: 10 minutes 19 seconds"),
                Result(state=State.OK, notice="\nPeer: de.pool.ntp.org"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:48 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 2"),
                Result(state=State.OK, notice="Next poll in: 10 minutes 13 seconds"),
            ],
            id="levels set to 3/4, one must fail => overall warn",
        ),
        pytest.param(
            (1, 2),
            True,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 3"),
                Result(state=State.OK, notice="\nPeer: time.facebook.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.WARN,
                    summary="time.facebook.com: Stratum: 1 (warn/crit at 1/2)",
                    details="Stratum: 1 (warn/crit at 1/2)",
                ),
                Result(state=State.OK, notice="Next poll in: 29 minutes 15 seconds"),
                Result(state=State.OK, notice="\nPeer: time.cloudflare.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:54 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.CRIT,
                    summary="time.cloudflare.com: Stratum: 3 (warn/crit at 1/2)",
                    details="Stratum: 3 (warn/crit at 1/2)",
                ),
                Result(state=State.OK, notice="Next poll in: 10 minutes 19 seconds"),
                Result(state=State.OK, notice="\nPeer: de.pool.ntp.org"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:48 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.CRIT,
                    summary="de.pool.ntp.org: Stratum: 2 (warn/crit at 1/2)",
                    details="Stratum: 2 (warn/crit at 1/2)",
                ),
                Result(state=State.OK, notice="Next poll in: 10 minutes 13 seconds"),
            ],
            id="all peers fail, worst state wins => overall crit",
        ),
        pytest.param(
            (6, 7),
            True,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="\nPeer: time.facebook.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 1"),
                Result(state=State.OK, notice="Next poll in: 29 minutes 15 seconds"),
                Result(state=State.OK, notice="\nPeer: time.cloudflare.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:54 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 3"),
                Result(state=State.OK, notice="Next poll in: 10 minutes 19 seconds"),
                Result(state=State.OK, notice="\nPeer: de.pool.ntp.org"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:41:48 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 2"),
                Result(state=State.OK, notice="Next poll in: 10 minutes 13 seconds"),
            ],
            id="no peers fail => overall ok",
        ),
    ],
)
def test_check_w32time_peers_summary(
    stratum_levels: tuple[int, int],
    universal: bool,
    expected: list[Result],
) -> None:
    parsed = w32time_peers.parse_w32time_peers(EN_PEERS_STRATUM_1_TO_3)
    params: w32time_peers.Params = {
        "reachability_consecutive_failures": ("no_levels", None),
        "reachability_total_failures": ("no_levels", None),
        "stratum": ("fixed", stratum_levels),
        "universal": universal,
    }
    result = list(w32time_peers.check_w32time_peers_summary(params, parsed))
    assert result == expected


@pytest.mark.parametrize(
    "universal, expected",
    [
        pytest.param(
            True,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 2 (alerts suppressed)"),
                Result(state=State.OK, notice="\nPeer: stratum-bad.example.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:00 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.OK,
                    notice="Stratum: 4 (warn/crit at 3/5) (alerts suppressed)",
                ),
                Result(state=State.OK, notice="Next poll in: 1 minute 40 seconds"),
                Result(state=State.OK, notice="\nPeer: reachability-bad.example.com"),
                Result(state=State.OK, notice="Last successful sync time: (null)"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 5"),
                Result(
                    state=State.OK,
                    notice="Consecutive failures (last 8 attempts): 3 (warn/crit at 2/3) (alerts suppressed)",
                ),
                Result(state=State.OK, notice="Last sync error: The peer is unreachable."),
                Result(
                    state=State.OK,
                    notice="Details from w32tm: This operation returned because the timeout period expired.",
                ),
                Result(state=State.OK, notice="Stratum: 1"),
                Result(state=State.OK, notice="Next poll in: 3 minutes 20 seconds"),
                Result(state=State.OK, notice="\nPeer: good.example.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:00:00 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 2"),
                Result(state=State.OK, notice="Next poll in: 5 minutes 0 seconds"),
            ],
            id="2/3 peers fail on different checks, universal=True => suppressed",
        ),
        pytest.param(
            False,
            [
                Result(state=State.OK, summary="Found 3 peers"),
                Result(state=State.OK, summary="Failed: 2"),
                Result(state=State.OK, notice="\nPeer: stratum-bad.example.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:00 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(
                    state=State.WARN,
                    summary="stratum-bad.example.com: Stratum: 4 (warn/crit at 3/5)",
                    details="Stratum: 4 (warn/crit at 3/5)",
                ),
                Result(state=State.OK, notice="Next poll in: 1 minute 40 seconds"),
                Result(state=State.OK, notice="\nPeer: reachability-bad.example.com"),
                Result(state=State.OK, notice="Last successful sync time: (null)"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 5"),
                Result(
                    state=State.CRIT,
                    summary="reachability-bad.example.com: Consecutive failures (last 8 attempts): 3 (warn/crit at 2/3)",
                    details="Consecutive failures (last 8 attempts): 3 (warn/crit at 2/3)",
                ),
                Result(state=State.OK, notice="Last sync error: The peer is unreachable."),
                Result(
                    state=State.OK,
                    notice="Details from w32tm: This operation returned because the timeout period expired.",
                ),
                Result(state=State.OK, notice="Stratum: 1"),
                Result(state=State.OK, notice="Next poll in: 3 minutes 20 seconds"),
                Result(state=State.OK, notice="\nPeer: good.example.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 6:00:00 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 2"),
                Result(state=State.OK, notice="Next poll in: 5 minutes 0 seconds"),
            ],
            id="2/3 peers fail on different checks, universal=False => worst state (crit)",
        ),
    ],
)
def test_check_w32time_peers_summary_mixed_failures(
    universal: bool,
    expected: list[Result],
) -> None:
    parsed = w32time_peers.parse_w32time_peers(EN_MIXED_FAILURES)
    params: w32time_peers.Params = {
        "reachability_consecutive_failures": ("fixed", (2, 3)),
        "reachability_total_failures": ("no_levels", None),
        "stratum": ("fixed", (3, 5)),
        "universal": universal,
    }
    result = list(w32time_peers.check_w32time_peers_summary(params, parsed))
    assert result == expected


@pytest.mark.parametrize(
    "fixture, expected",
    [
        pytest.param(
            NO_PEERS,
            [
                Result(state=State.OK, summary="Found 0 peers"),
                Result(state=State.OK, summary="Failed: 0"),
            ],
            id="no peers",
        ),
        pytest.param(
            EN_SINGLE_PEER,
            [
                Result(state=State.OK, summary="Found 1 peer"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="\nPeer: time.facebook.com"),
                Result(state=State.OK, notice="Last successful sync time: 9/18/2025 7:00:50 PM"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 1"),
                Result(state=State.OK, notice="Next poll in: 29 minutes 15 seconds"),
            ],
            id="single peer",
        ),
    ],
)
def test_check_w32time_peers_summary_edge_cases(
    fixture: StringTable, expected: CheckResult
) -> None:
    """
    We should not crash in edge cases like no peers or a single peer.
    """
    parsed = w32time_peers.parse_w32time_peers(fixture)
    params: w32time_peers.Params = {
        "reachability_consecutive_failures": ("no_levels", None),
        "reachability_total_failures": ("no_levels", None),
        "stratum": ("no_levels", None),
        "universal": False,
    }
    result = list(w32time_peers.check_w32time_peers_summary(params, parsed))
    assert result == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            DE_MISSING_PEER_NAME,
            [
                Result(state=State.OK, summary="Found 1 peer"),
                Result(state=State.OK, summary="Failed: 1"),
                Result(state=State.WARN, summary="1 peer with no name found!"),
            ],
        ),
        (
            DE_MULTIPLE_MISSING_PEER_NAMES,
            [
                Result(state=State.OK, summary="Found 2 peers"),
                Result(state=State.OK, summary="Failed: 2"),
                Result(state=State.WARN, summary="2 peers with no name found!"),
            ],
        ),
        (
            DE_MIXED_MISSING_PEER_NAME,
            [
                Result(state=State.OK, summary="Found 2 peers"),
                Result(state=State.OK, summary="Failed: 1"),
                Result(state=State.WARN, summary="1 peer with no name found!"),
                Result(state=State.OK, notice="\nPeer: time.cloudflare.com"),
                Result(state=State.OK, notice="Last successful sync time: 07.03.2026 04:17:06"),
                Result(state=State.OK, notice="Total failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Consecutive failures (last 8 attempts): 0"),
                Result(state=State.OK, notice="Stratum: 3"),
                Result(state=State.OK, notice="Next poll in: 50 minutes 17 seconds"),
            ],
        ),
    ],
)
def test_check_w32time_peers_summary_missing_peer_name(
    string_table: StringTable, expected: CheckResult
) -> None:
    """
    Handle missing peer names correctly.
    """
    parsed = w32time_peers.parse_w32time_peers(string_table)
    params: w32time_peers.Params = {
        "reachability_consecutive_failures": ("no_levels", None),
        "reachability_total_failures": ("no_levels", None),
        "stratum": ("no_levels", None),
        "universal": False,
    }
    result = list(w32time_peers.check_w32time_peers_summary(params, parsed))
    assert result == expected


@pytest.mark.parametrize(
    "binary, exp_total, exp_consecutive, exp_attempts",
    [
        (0b101, 1, 0, 3),
        (0b101000, 4, 3, 6),
        (0b11111111, 0, 0, 8),
        (0b111, 0, 0, 3),
        (0b000, 1, 1, 1),
    ],
)
def test_compute_failures(
    binary: int, exp_total: int, exp_consecutive: int, exp_attempts: int
) -> None:
    reachability = w32time_peers.Reachability.from_raw(binary, 1)
    assert reachability.total_failures == exp_total
    assert reachability.consecutive_failures == exp_consecutive
    assert reachability.total_attempts == exp_attempts
