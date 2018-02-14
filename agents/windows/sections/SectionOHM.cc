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

#include "SectionOHM.h"
#include "Configuration.h"
#include "Environment.h"
#include "Logger.h"
#include "OHMMonitor.h"
#include "SectionWMI.h"

SectionOHM::SectionOHM(Configuration &config, Logger *logger,
                       const WinApiAdaptor &winapi)
    : SectionWMI("openhardwaremonitor", "openhardwaremonitor",
                 config.getEnvironment(), logger, winapi)
    , _ohm_monitor(_env.binDirectory(), _logger, _winapi) {
    withNamespace(L"Root\\OpenHardwareMonitor");
    withObject(L"Sensor");
}

void SectionOHM::startIfAsync() { _ohm_monitor.startProcess(); }

bool SectionOHM::produceOutputInner(std::ostream &out) {
    Debug(_logger) << "SectionOHM::produceOutputInner";
    bool res = false;
    try {
        res = SectionWMI::produceOutputInner(out);
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
