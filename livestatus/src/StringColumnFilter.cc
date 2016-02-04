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

#include "StringColumnFilter.h"
#include <stdlib.h>
#include <string.h>
#include "OutputBuffer.h"
#include "StringColumn.h"
#include "logger.h"
#include "opids.h"

StringColumnFilter::StringColumnFilter(StringColumn *column, int opid,
                                       char *value)
    : _column(column)
    , _ref_string(value)
    , _opid(abs(opid))
    , _negate(opid < 0)
    , _regex(nullptr) {
    if (_opid == OP_REGEX || _opid == OP_REGEX_ICASE) {
        if ((strchr(value, '{') != nullptr) ||
            (strchr(value, '}') != nullptr)) {
            setError(
                RESPONSE_CODE_INVALID_HEADER,
                "disallowed regular expression '%s': must not contain { or }",
                value);
        } else {
            _regex = new regex_t();
            if (0 != regcomp(_regex, value,
                             REG_EXTENDED | REG_NOSUB |
                                 (_opid == OP_REGEX_ICASE ? REG_ICASE : 0))) {
                setError(RESPONSE_CODE_INVALID_HEADER,
                         "invalid regular expression '%s'", value);
                delete _regex;
                _regex = nullptr;
            }
        }
    }
}

StringColumnFilter::~StringColumnFilter() {
    if (_regex != nullptr) {
        regfree(_regex);
        delete _regex;
    }
}

bool StringColumnFilter::accepts(void *data) {
    bool pass = true;
    const char *act_string = _column->getValue(data);
    if (act_string == nullptr) {
        act_string =
            "";  // e.g. current_service_perf_data in host entry in log table
    }
    switch (_opid) {
        case OP_EQUAL:
            pass = _ref_string == act_string;
            break;
        case OP_EQUAL_ICASE:
            pass = (strcasecmp(_ref_string.c_str(), act_string) == 0);
            break;
        case OP_REGEX:
        case OP_REGEX_ICASE:
            pass = _regex != nullptr &&
                   0 == regexec(_regex, act_string, 0, nullptr, 0);
            break;
        case OP_GREATER:
            pass = 0 > strcmp(_ref_string.c_str(), act_string);
            break;
        case OP_LESS:
            pass = 0 < strcmp(_ref_string.c_str(), act_string);
            break;
        default:
            // this should never be reached, all operators are handled
            logger(LG_INFO, "Sorry. Operator %s for strings not implemented.",
                   op_names_plus_8[_opid]);
            break;
    }
    return pass != _negate;
}

void *StringColumnFilter::indexFilter(const char *column) {
    if (_opid == OP_EQUAL && (strcmp(column, _column->name()) == 0)) {
        // TODO(sp) The cast looks very dubious, but the whole void* story is
        // quite dangerous...
        return const_cast<char *>(_ref_string.c_str());
    }
    return nullptr;
}
