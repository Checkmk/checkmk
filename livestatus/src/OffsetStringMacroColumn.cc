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
#include <cstring>
#include <memory>
#include "Filter.h"
#include "Logger.h"
#include "Renderer.h"
#include "Row.h"
#include "VariadicFilter.h"

using std::string;
using std::unique_ptr;

extern char *macro_user[MAX_USER_MACROS];

void OffsetStringMacroColumn::output(Row row, RowRenderer &r,
                                     const contact * /*unused*/) const {
    string raw = getValue(row);
    host *hst = getHost(row);
    service *svc = getService(row);

    // search for macro names, beginning with $
    string result;
    const char *scan = raw.c_str();

    while (*scan != 0) {
        const char *dollar = strchr(scan, '$');
        if (dollar == nullptr) {
            result += scan;
            break;
        }
        result += string(scan, dollar - scan);
        const char *otherdollar = strchr(dollar + 1, '$');
        if (otherdollar == nullptr) {  // unterminated macro, do not expand
            result += scan;
            break;
        }
        string macroname = string(dollar + 1, otherdollar - dollar - 1);
        const char *replacement = expandMacro(macroname.c_str(), hst, svc);
        if (replacement != nullptr) {
            result += replacement;
        } else {
            result += string(
                dollar, otherdollar - dollar + 1);  // leave macro unexpanded
        }
        scan = otherdollar + 1;
    }
    r.output(result);
}

unique_ptr<Filter> OffsetStringMacroColumn::createFilter(
    RelationalOperator /*unused */, const string & /*unused*/) const {
    Informational(logger())
        << "Sorry. No filtering on macro columns implemented yet";
    return VariadicFilter::make(LogicalOperator::and_);
}

const char *OffsetStringMacroColumn::expandMacro(const char *macroname,
                                                 host *hst,
                                                 service *svc) const {
    // host macros
    if (strcmp(macroname, "HOSTNAME") == 0) {
        return hst->name;
    }
    if (strcmp(macroname, "HOSTDISPLAYNAME") == 0) {
        return hst->display_name;
    }
    if (strcmp(macroname, "HOSTALIAS") == 0) {
        return hst->alias;
    }
    if (strcmp(macroname, "HOSTADDRESS") == 0) {
        return hst->address;
    }
    if (strcmp(macroname, "HOSTOUTPUT") == 0) {
        return hst->plugin_output;
    }
    if (strcmp(macroname, "LONGHOSTOUTPUT") == 0) {
        return hst->long_plugin_output;
    }
    if (strcmp(macroname, "HOSTPERFDATA") == 0) {
        return hst->perf_data;
    }
    if (strcmp(macroname, "HOSTCHECKCOMMAND") == 0) {
#ifndef NAGIOS4
        return hst->host_check_command;
#else
        return hst->check_command;
#endif  // NAGIOS4
    }
    if (strncmp(macroname, "_HOST", 5) == 0) {  // custom macro
        return expandCustomVariables(macroname + 5, hst->custom_variables);

        // service macros
    }
    if (svc != nullptr) {
        if (strcmp(macroname, "SERVICEDESC") == 0) {
            return svc->description;
        }
        if (strcmp(macroname, "SERVICEDISPLAYNAME") == 0) {
            return svc->display_name;
        }
        if (strcmp(macroname, "SERVICEOUTPUT") == 0) {
            return svc->plugin_output;
        }
        if (strcmp(macroname, "LONGSERVICEOUTPUT") == 0) {
            return svc->long_plugin_output;
        }
        if (strcmp(macroname, "SERVICEPERFDATA") == 0) {
            return svc->perf_data;
        }
        if (strcmp(macroname, "SERVICECHECKCOMMAND") == 0) {
#ifndef NAGIOS4
            return svc->service_check_command;
#else
            return svc->check_command;
#endif  // NAGIOS4
        }
        if (strncmp(macroname, "_SERVICE", 8) == 0) {  // custom macro
            return expandCustomVariables(macroname + 8, svc->custom_variables);
        }
    }

    // USER macros
    if (strncmp(macroname, "USER", 4) == 0) {
        int n = atoi(macroname + 4);
        if (n > 0 && n <= MAX_USER_MACROS) {
            return macro_user[n - 1];
        }
    }

    return nullptr;
}

const char *OffsetStringMacroColumn::expandCustomVariables(
    const char *varname, customvariablesmember *custvars) const {
    for (; custvars != nullptr; custvars = custvars->next) {
        if (strcasecmp(varname, custvars->variable_name) == 0) {
            return custvars->variable_value;
        }
    }
    return nullptr;
}
