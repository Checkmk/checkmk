// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionOHM.h"
#include "Configuration.h"
#include "Environment.h"
#include "Logger.h"
#include "OHMMonitor.h"
#include "SectionWMI.h"

SectionOHM::SectionOHM(Configuration &config, Logger *logger,
                       const WinApiInterface &winapi)
    : SectionWMI("openhardwaremonitor", "openhardwaremonitor",
                 config.getEnvironment(), logger, winapi)
    , _ohm_monitor(_env.binDirectory(), _logger, _winapi) {
    withNamespace(L"Root\\OpenHardwareMonitor");
    withObject(L"Sensor");
}

void SectionOHM::startIfAsync() { _ohm_monitor.startProcess(); }

bool SectionOHM::produceOutputInner(
    std::ostream &out, const std::optional<std::string> &remoteIP) {
    Debug(_logger) << "SectionOHM::produceOutputInner";
    bool res = false;
    try {
        res = SectionWMI::produceOutputInner(out, remoteIP);
    } catch (const wmi::ComException &e) {
        Debug(_logger) << "ComException: " << e.what();
        res = false;
    }
    if (!res && !_ohm_monitor.startProcess()) {
        Debug(_logger)
            << "ohm not installed or not runnable -> section disabled";
        suspend(3600);
    }
    return res;
    // if ohm was started here, we still don't query the data again this
    // cycle because it's impossible to predict how long the ohm client
    // takes to start up but it won't be instantanious
}
