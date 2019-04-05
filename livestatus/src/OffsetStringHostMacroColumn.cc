// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "OffsetStringHostMacroColumn.h"
#include "Row.h"
#include "nagios.h"

HostMacroExpander::HostMacroExpander(const host *hst)
    : _hst(hst), _cve("_HOST", hst->custom_variables) {}

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
        std::make_unique<HostMacroExpander>(columnData<host>(row)),
        std::make_unique<UserMacroExpander>());
}
