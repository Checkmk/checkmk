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

#ifdef CMC
#include <unordered_set>
#include "World.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

HostListFilter::HostListFilter(const HostListColumn &column,
                               RelationalOperator relOp, std::string value)
    : _column(column), _relOp(relOp), _ref_value(std::move(value)) {}

namespace {
bool isEmpty(HostListColumn::host_list hostlist) {
#ifdef CMC
    return hostlist->empty();
#else
    return hostlist == nullptr;
#endif
}

bool contains(HostListColumn::host_list hostlist,
              const std::string &ref_value) {
#ifdef CMC
    return hostlist->find(g_live_world->getHost(ref_value)) != hostlist->end();
#else
    for (; hostlist != nullptr; hostlist = hostlist->next) {
        char *host_name = hostlist->host_name;
        if (host_name == nullptr) {
            host_name = hostlist->host_ptr->name;
        }
        if (host_name == ref_value) {
            return true;
        }
    }
    return false;
#endif
}
}  // namespace

bool HostListFilter::accepts(Row row, const contact * /* auth_user */,
                             std::chrono::seconds /* timezone_offset */) const {
    auto hostlist = _column.getMembers(row);
    switch (_relOp) {
        case RelationalOperator::equal:
            if (!_ref_value.empty()) {
                Informational(_column.logger())
                    << "Sorry, equality for host lists implemented only for emptiness";
                return false;
            }
            return isEmpty(hostlist);
        case RelationalOperator::not_equal:
            if (!_ref_value.empty()) {
                Informational(_column.logger())
                    << "Sorry, inequality for host lists implemented only for emptiness";
                return false;
            }
            return !isEmpty(hostlist);
        case RelationalOperator::less:
            return !contains(hostlist, _ref_value);
        case RelationalOperator::greater_or_equal:
            return contains(hostlist, _ref_value);
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

std::string HostListFilter::columnName() const { return _column.name(); }
