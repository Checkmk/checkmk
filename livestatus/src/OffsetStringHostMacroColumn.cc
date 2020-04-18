// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetStringHostMacroColumn.h"
#include "Row.h"
#include "nagios.h"

HostMacroExpander::HostMacroExpander(const host *hst, const MonitoringCore *mc)
    : _hst(hst), _cve("_HOST", hst->custom_variables, mc) {}

std::optional<std::string> HostMacroExpander::expand(const std::string &str) {
    if (str == "HOSTNAME") {
        return from_ptr(_hst->name);
    }
    if (str == "HOSTDISPLAYNAME") {
        return from_ptr(_hst->display_name);
    }
    if (str == "HOSTALIAS") {
        return from_ptr(_hst->alias);
    }
    if (str == "HOSTADDRESS") {
        return from_ptr(_hst->address);
    }
    if (str == "HOSTOUTPUT") {
        return from_ptr(_hst->plugin_output);
    }
    if (str == "LONGHOSTOUTPUT") {
        return from_ptr(_hst->long_plugin_output);
    }
    if (str == "HOSTPERFDATA") {
        return from_ptr(_hst->perf_data);
    }
    if (str == "HOSTCHECKCOMMAND") {
#ifndef NAGIOS4
        return from_ptr(_hst->host_check_command);
#else
        return from_ptr(_hst->check_command);
#endif  // NAGIOS4
    }
    return _cve.expand(str);
}

std::unique_ptr<MacroExpander> OffsetStringHostMacroColumn::getMacroExpander(
    Row row) const {
    return std::make_unique<CompoundMacroExpander>(
        std::make_unique<HostMacroExpander>(columnData<host>(row), _mc),
        std::make_unique<UserMacroExpander>());
}
