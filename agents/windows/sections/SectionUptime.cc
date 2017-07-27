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

#define _WIN32_WINNT 0x0600

#include "SectionUptime.h"
#include "../Environment.h"
#include "../LoggerAdaptor.h"
#include "../dynamic_func.h"
#define WIN32_LEAN_AND_MEAN

SectionUptime::SectionUptime(const Environment &env, LoggerAdaptor &logger,
                             const WinApiAdaptor &winapi)
    : Section("uptime", env, logger, winapi) {
    LPCWSTR dllName = L"kernel32.dll";
    LPCSTR funcName = "GetTickCount64";
    GetTickCount64_dyn =
        dynamic_func<GetTickCount64_type>(dllName, funcName, _winapi);
    if (GetTickCount64_dyn == nullptr) {
        // GetTickCount64 is only available on Vista/2008 and newer
        _wmi_helper.reset(new wmi::Helper(_winapi, L"Root\\cimv2"));
    }
}

bool SectionUptime::produceOutputInner(std::ostream &out) {
    if (GetTickCount64_dyn != nullptr) {
        out << outputTickCount64();
    } else if (_wmi_helper.get() != nullptr) {
        out << outputWMI();
    }
    return true;
}

std::string SectionUptime::outputTickCount64() {
    return std::to_string(GetTickCount64_dyn() / 1000);
}

std::string SectionUptime::outputWMI() {
    int tries = 2;
    while (tries-- > 0) {
        try {
            wmi::Result res = _wmi_helper->query(
                L"SELECT SystemUpTime FROM "
                L"Win32_PerfFormattedData_PerfOS_System");
            if (res.valid()) {
                return res.get<std::string>(L"SystemUpTime");
            }
        } catch (const wmi::ComException &e) {
            _logger.crashLog("wmi request for SystemUpTime failed: %s",
                             e.what());
        }
    }
    // TODO: wmi appears to be unreliable on some systems so maybe switch
    // to another fallback?
    return "0";
}
