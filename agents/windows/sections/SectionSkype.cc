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
#include "../Logger.h"
#include "../PerfCounterCommon.h"
#include "../WinApiAdaptor.h"
#include "../stringutil.h"
#include "SectionPerfcounter.h"

namespace {

int getCounterName(
    const WinApiAdaptor &winapi,
    const std::array<std::unordered_map<std::string, DWORD>, 2> &nameIdMaps,
    const std::string &counterName, Logger *logger) {
    for (const auto &nameIdMap : nameIdMaps) {
        const auto it = nameIdMap.find(counterName);

        if (it != nameIdMap.end()) {
            return it->second;
        }
    }
    Debug(logger) << "SectionSkype::SectionSkype "
                  << "could not resolve counter name " << counterName;
    return -1;
}

}  // namespace

SectionSkype::SectionSkype(const Environment &env, Logger *logger,
                           const WinApiAdaptor &winapi)
    : SectionGroup("skype", "skype", env, logger, winapi) {
    withToggleIfMissing();
    withNestedSubtables();
    withSeparator(',');

    const std::array<std::unordered_map<std::string, DWORD>, 2> nameIdMaps = {
        perf_name_map<char>(_winapi, false),
        perf_name_map<char>(_winapi, true)};

    for (const std::string &counterName :
         {"LS:WEB - Address Book Web Query",
          "LS:WEB - Address Book File Download",
          "LS:WEB - Location Information Service",
          "LS:WEB - Distribution List Expansion",
          "LS:WEB - UCWA",
          "LS:WEB - Mobile Communication Service",
          "LS:WEB - Throttling and Authentication",
          "LS:WEB - Auth Provider related calls",
          "LS:SIP - Protocol",
          "LS:SIP - Responses",
          "LS:SIP - Peers",
          "LS:SIP - Load Management",
          "LS:SIP - Authentication",
          "LS:CAA - Operations",
          "LS:DATAMCU - MCU Health And Performance",
          "LS:AVMCU - MCU Health And Performance",
          "LS:AsMcu - MCU Health And Performance",
          "LS:ImMcu - MCU Health And Performance",
          "LS:USrv - DBStore",
          "LS:USrv - Conference Mcu Allocator",
          "LS:JoinLauncher - Join Launcher Service Failures",
          "LS:MediationServer - Health Indices",
          "LS:MediationServer - Global Counters",
          "LS:MediationServer - Global Per Gateway Counters",
          "LS:MediationServer - Media Relay",
          "LS:A/V Auth - Requests",
          "LS:DATAPROXY - Server Connections",
          "LS:XmppFederationProxy - Streams",
          "LS:A/V Edge - TCP Counters",
          "LS:A/V Edge - UDP Counters"}) {
        int counterId =
            getCounterName(_winapi, nameIdMaps, counterName, _logger);
        if (counterId >= 0) {
            withSubSection(new SectionPerfcounter(
                counterName, counterName, counterId, _env, _logger, _winapi));
        }
    }

    // TODO the version number in the counter name isn't exactly inspiring
    // trust, but there currently is no support for wildcards.
    const std::string counterName = "ASP.NET Apps v4.0.30319";
    int counterId = getCounterName(_winapi, nameIdMaps, counterName, _logger);
    if (counterId >= 0) {
        withDependentSubSection(new SectionPerfcounter(
            counterName, counterName, counterId, _env, _logger, _winapi));
    }
}

bool SectionSkype::produceOutputInner(std::ostream &out) {
    LARGE_INTEGER Counter, Frequency;
    _winapi.QueryPerformanceCounter(&Counter);
    _winapi.QueryPerformanceFrequency(&Frequency);

    out << "sampletime," << Counter.QuadPart << "," << Frequency.QuadPart
        << "\n";

    return SectionGroup::produceOutputInner(out);
}
