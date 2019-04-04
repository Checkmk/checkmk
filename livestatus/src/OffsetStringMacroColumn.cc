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

#include "OffsetStringMacroColumn.h"
#include <cstdlib>
#include "Column.h"
#include "RegExp.h"
#include "Row.h"
#include "StringUtils.h"

std::string OffsetStringMacroColumn::getValue(Row row) const {
    // TODO(sp): Use _mc!
    (void)_mc;
    if (auto p = columnData<void>(row)) {
        auto s = offset_cast<const char *>(p, _string_offset);
        return *s == nullptr ? ""
                             : expandMacros(*s, getHost(row), getService(row));
    }
    return "";
}

// static
std::string OffsetStringMacroColumn::expandMacros(const std::string &raw,
                                                  const host *hst,
                                                  const service *svc) {
    std::string result;
    size_t pos = 0;
    while (pos < raw.size()) {
        auto start = raw.find('$', pos);
        if (start == std::string::npos) {
            result += raw.substr(pos);
            break;
        }
        auto end = raw.find('$', start + 1);
        if (end == std::string::npos) {
            result += raw.substr(pos);
            break;
        }
        auto macroname = raw.substr(start + 1, end - (start + 1));
        if (auto replacement = expandMacro(macroname, hst, svc)) {
            result += raw.substr(pos, start - pos) + replacement;
        } else {
            result += raw.substr(pos, end + 1 - pos);
        }
        pos = end + 1;
    }
    return result;
}

// static
const char *OffsetStringMacroColumn::expandMacro(const std::string &macroname,
                                                 const host *hst,
                                                 const service *svc) {
    // host macros
    if (macroname == "HOSTNAME") {
        return hst->name;
    }
    if (macroname == "HOSTDISPLAYNAME") {
        return hst->display_name;
    }
    if (macroname == "HOSTALIAS") {
        return hst->alias;
    }
    if (macroname == "HOSTADDRESS") {
        return hst->address;
    }
    if (macroname == "HOSTOUTPUT") {
        return hst->plugin_output;
    }
    if (macroname == "LONGHOSTOUTPUT") {
        return hst->long_plugin_output;
    }
    if (macroname == "HOSTPERFDATA") {
        return hst->perf_data;
    }
    if (macroname == "HOSTCHECKCOMMAND") {
#ifndef NAGIOS4
        return hst->host_check_command;
#else
        return hst->check_command;
#endif  // NAGIOS4
    }
    if (mk::starts_with(macroname, "_HOST")) {  // custom macro
        return expandCustomVariables(macroname.substr(5),
                                     hst->custom_variables);

        // service macros
    }
    if (svc != nullptr) {
        if (macroname == "SERVICEDESC") {
            return svc->description;
        }
        if (macroname == "SERVICEDISPLAYNAME") {
            return svc->display_name;
        }
        if (macroname == "SERVICEOUTPUT") {
            return svc->plugin_output;
        }
        if (macroname == "LONGSERVICEOUTPUT") {
            return svc->long_plugin_output;
        }
        if (macroname == "SERVICEPERFDATA") {
            return svc->perf_data;
        }
        if (macroname == "SERVICECHECKCOMMAND") {
#ifndef NAGIOS4
            return svc->service_check_command;
#else
            return svc->check_command;
#endif  // NAGIOS4
        }
        if (mk::starts_with(macroname, "_SERVICE")) {  // custom macro
            return expandCustomVariables(macroname.substr(8),
                                         svc->custom_variables);
        }
    }

    // USER macros
    if (mk::starts_with(macroname, "USER")) {
        int n = atoi(macroname.substr(4).c_str());
        if (n > 0 && n <= MAX_USER_MACROS) {
            extern char *macro_user[MAX_USER_MACROS];
            return macro_user[n - 1];
        }
    }

    return nullptr;
}

// static
const char *OffsetStringMacroColumn::expandCustomVariables(
    const std::string &varname, const customvariablesmember *custvars) {
    RegExp regExp(varname, RegExp::Case::ignore, RegExp::Syntax::literal);
    for (; custvars != nullptr; custvars = custvars->next) {
        if (regExp.match(custvars->variable_name)) {
            return custvars->variable_value;
        }
    }
    return nullptr;
}
