// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionUptime.h"
#include "Environment.h"
#include "Logger.h"
#include "SectionHeader.h"
#include "dynamic_func.h"

SectionUptime::SectionUptime(const Environment &env, Logger *logger,
                             const WinApiInterface &winapi)
    : Section("uptime", env, logger, winapi,
              std::make_unique<DefaultHeader>("uptime", logger)) {
    LPCWSTR dllName = L"kernel32.dll";
    LPCSTR funcName = "GetTickCount64";
    GetTickCount64_dyn =
        dynamic_func<GetTickCount64_type>(dllName, funcName, _winapi);
    if (GetTickCount64_dyn == nullptr) {
        // GetTickCount64 is only available on Vista/2008 and newer
        _wmi_helper.reset(new wmi::Helper(_logger, _winapi, L"Root\\cimv2"));
    }
}

bool SectionUptime::produceOutputInner(std::ostream &out,
                                       const std::optional<std::string> &) {
    Debug(_logger) << "SectionUptime::produceOutputInner";
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
    Debug(_logger) << "SectionUptime::outputWMI";
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
            Error(_logger) << "wmi request for SystemUpTime failed: "
                           << e.what();
        }
    }
    // TODO: wmi appears to be unreliable on some systems so maybe switch
    // to another fallback?
    return "0";
}
