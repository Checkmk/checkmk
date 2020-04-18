// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetStringServiceMacroColumn.h"
#include <optional>
#include "OffsetStringHostMacroColumn.h"
#include "Row.h"
#include "nagios.h"

ServiceMacroExpander::ServiceMacroExpander(const service *svc,
                                           const MonitoringCore *mc)
    : _svc(svc), _cve("_SERVICE", svc->custom_variables, mc) {}

std::optional<std::string> ServiceMacroExpander::expand(
    const std::string &str) {
    if (str == "SERVICEDESC") {
        return from_ptr(_svc->description);
    }
    if (str == "SERVICEDISPLAYNAME") {
        return from_ptr(_svc->display_name);
    }
    if (str == "SERVICEOUTPUT") {
        return from_ptr(_svc->plugin_output);
    }
    if (str == "LONGSERVICEOUTPUT") {
        return from_ptr(_svc->long_plugin_output);
    }
    if (str == "SERVICEPERFDATA") {
        return from_ptr(_svc->perf_data);
    }
    if (str == "SERVICECHECKCOMMAND") {
#ifndef NAGIOS4
        return from_ptr(_svc->service_check_command);
#else
        return from_ptr(_svc->check_command);
#endif  // NAGIOS4
    }
    return _cve.expand(str);
}

std::unique_ptr<MacroExpander> OffsetStringServiceMacroColumn::getMacroExpander(
    Row row) const {
    auto svc = columnData<service>(row);
    return std::make_unique<CompoundMacroExpander>(
        std::make_unique<HostMacroExpander>(svc->host_ptr, _mc),
        std::make_unique<CompoundMacroExpander>(
            std::make_unique<ServiceMacroExpander>(svc, _mc),
            std::make_unique<UserMacroExpander>()));
}
