// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "SectionSkype.h"
#include "SectionPerfcounter.h"
#include "../stringutil.h"
#include <windows.h>

SectionSkype::SectionSkype(const Environment &env, LoggerAdaptor &logger)
    : SectionGroup("skype", env, logger) {
    withToggleIfMissing();
    withFailIfMissing();
    withNestedSubtables();
    withSeparator(',');

    for (LPCWSTR data_source :
         {L"LS:WEB - Address Book Web Query",
          L"LS:WEB - Address Book File Download",
          L"LS:WEB - Location Information Service",
          L"LS:WEB - Distribution List Expansion",
          L"LS:WEB - UCWA",
          L"LS:WEB - Mobile Communication Service",
          L"LS:WEB - Throttling and Authentication",
          L"LS:WEB - Auth Provider related calls",
          L"LS:SIP - Protocol",
          L"LS:SIP - Responses",
          L"LS:SIP - Peers",
          L"LS:SIP - Load Management",
          L"LS:SIP - Authentication",
          L"LS:CAA - Operations",
          L"LS:DATAMCU - MCU Health And Performance",
          L"LS:AVMCU - MCU Health And Performance",
          L"LS:AsMcu - MCU Health And Performance",
          L"LS:ImMcu - MCU Health And Performance",
          L"LS:USrv - DBStore",
          L"LS:USrv - Conference Mcu Allocator",
          L"LS:JoinLauncher - Join Launcher Service Failure",
          L"LS:MediationServer - Health Indices",
          L"LS:MediationServer - Global Counters",
          L"LS:MediationServer - Global Per Gateway Counters",
          L"LS:MediationServer - Media Relay",
          L"LS:A/V Auth - Requests",
          L"LS:DATAPROXY - Server Connections",
          L"LS:XmppFederationProxy - Streams",
          L"LS:A/V Edge - TCP Counters",
          L"LS:A/V Edge - UDP Counters"}) {
        withSubSection((new SectionPerfcounter(to_utf8(data_source).c_str(), _env, _logger))
                           ->withCounter(data_source));
    }

    // TODO the version number in the counter name isn't exactly inspiring
    // trust,
    // but there currently is no support for wildcards.
    withDependentSubSection((new SectionPerfcounter("ASP.NET Apps v4.0.30319", _env, _logger))
                                ->withCounter(L"ASP.NET Apps v4.0.30319"));
}

bool SectionSkype::produceOutputInner(std::ostream &out) {
    LARGE_INTEGER Counter, Frequency;
    QueryPerformanceCounter(&Counter);
    QueryPerformanceFrequency(&Frequency);

    out << "sampletime," << Counter.QuadPart << "," << Frequency.QuadPart
        << "\n";

    return SectionGroup::produceOutputInner(out);
}

