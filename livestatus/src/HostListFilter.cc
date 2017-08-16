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

#include "HostListFilter.h"
#include <ostream>
#include <utility>
#include "HostListColumn.h"
#include "Logger.h"
#include "Row.h"
#include "nagios.h"

using std::move;
using std::string;

HostListFilter::HostListFilter(const HostListColumn &column,
                               RelationalOperator relOp, string value)
    : _column(column), _relOp(relOp), _ref_value(move(value)) {}

bool HostListFilter::accepts(Row row, contact * /* auth_user */,
                             int /* timezone_offset */) const {
    // data points to a primary data object. We need to extract a pointer to a
    // host list
    hostsmember *mem = _column.getMembers(row);

    // test for empty list
    if (_ref_value.empty()) {
        if (_relOp == RelationalOperator::equal) {
            return mem == nullptr;
        }
        if (_relOp == RelationalOperator::not_equal) {
            return mem != nullptr;
        }
    }

    bool is_member = false;
    for (; mem != nullptr; mem = mem->next) {
        char *host_name = mem->host_name;
        if (host_name == nullptr) {
            host_name = mem->host_ptr->name;
        }

        if (host_name == _ref_value) {
            is_member = true;
            break;
        }
    }

    switch (_relOp) {
        case RelationalOperator::less:
            return !is_member;
        case RelationalOperator::greater_or_equal:
            return is_member;
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            Informational(_column.logger())
                << "Sorry. Operator " << _relOp
                << " for host lists not implemented.";
            return false;
    }
    return false;  // unreachable
}

string HostListFilter::columnName() const { return _column.name(); }
