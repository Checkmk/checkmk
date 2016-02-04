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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "OffsetStringMacroColumn.h"
#include <stdlib.h>
#include <string.h>
#include "AndingFilter.h"
#include "Query.h"
#include "logger.h"
class Filter;

using std::string;

extern char *macro_user[MAX_USER_MACROS];

string OffsetStringMacroColumn::valueAsString(void *data, Query * /*unused*/) {
    const char *raw = getValue(data);
    host *hst = getHost(data);
    service *svc = getService(data);

    // search for macro names, beginning with $
    string result = "";
    const char *scan = raw;

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
    return result;
}

void OffsetStringMacroColumn::output(void *data, Query *query) {
    string s = valueAsString(data, query);
    query->outputString(s.c_str());
}

Filter *OffsetStringMacroColumn::createFilter(int /*operator_id*/,
                                              char * /*value*/) {
    logger(LG_INFO, "Sorry. No filtering on macro columns implemented yet");
    return new AndingFilter();  // always true
}

const char *OffsetStringMacroColumn::expandMacro(const char *macroname,
                                                 host *hst, service *svc) {
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
    const char *varname, customvariablesmember *custvars) {
    while (custvars != nullptr) {
        if (strcasecmp(varname, custvars->variable_name) == 0) {
            return custvars->variable_value;
        }
        custvars = custvars->next;
    }
    return nullptr;
}
