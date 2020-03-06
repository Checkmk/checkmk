// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionSkype.h"

#include "Logger.h"
#include "PerfCounterCommon.h"
#include "SectionHeader.h"
#include "WinApiInterface.h"
#include "stringutil.h"

SectionSkype::SectionSkype(const Environment &env, Logger *logger,
                           const WinApiInterface &winapi)
    : SectionGroup("skype", "skype", env, logger, winapi, true)
    , _nameNumberMap(_logger, _winapi) {
    withToggleIfMissing();

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
        withSubSection(new SectionPerfcounter(
            counterName, counterName, _env, _nameNumberMap, _logger, _winapi));
    }

    // TODO the version number in the counter name isn't exactly inspiring
    // trust, but there currently is no support for wildcards.
    const std::string counterName = "ASP.NET Apps v4.0.30319";
    withDependentSubSection(new SectionPerfcounter(
        counterName, counterName, _env, _nameNumberMap, _logger, _winapi));

    // ***************************************************************************
    // Hammer is only effective method to force skype to use ',' instead of
    // wmi/section_group(!) '|' as a separator
    // This legacy code is not good, but frozen
    // Hierarchy, structure and testing should not be changed
    // Only local error fixing is allowed
    // ***************************************************************************
    // overwrite with correct header.
    _header =
        std::make_unique<SectionHeader<',', SectionBrackets>>("skype", logger);
}

bool SectionSkype::produceOutputInner(
    std::ostream &out, const std::optional<std::string> &remoteIP) {
    Debug(_logger) << "SectionSkype::produceOutputInner";
    LARGE_INTEGER Counter, Frequency;
    _winapi.QueryPerformanceCounter(&Counter);
    _winapi.QueryPerformanceFrequency(&Frequency);

    out << "sampletime," << Counter.QuadPart << "," << Frequency.QuadPart
        << "\n";

    return SectionGroup::produceOutputInner(out, remoteIP);
}
