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

#include "HostListColumn.h"
#include "Filter.h"
#include "HostListFilter.h"
#include "Renderer.h"
#include "Row.h"
#include "auth.h"

using std::make_unique;
using std::string;
using std::unique_ptr;

hostsmember *HostListColumn::getMembers(Row row) const {
    if (auto p = columnData<void>(row)) {
        return *offset_cast<hostsmember *>(p, _offset);
    }
    return nullptr;
}

void HostListColumn::output(Row row, RowRenderer &r,
                            const contact *auth_user) const {
    ListRenderer l(r);
    for (hostsmember *mem = getMembers(row); mem != nullptr; mem = mem->next) {
        host *hst = mem->host_ptr;
        if (auth_user == nullptr ||
            is_authorized_for(_mc, auth_user, hst, nullptr)) {
            if (!_show_state) {
                l.output(string(hst->name));
            } else {
                SublistRenderer s(l);
                s.output(string(hst->name));
                s.output(hst->current_state);
                s.output(hst->has_been_checked);
            }
        }
    }
}

unique_ptr<Filter> HostListColumn::createFilter(RelationalOperator relOp,
                                                const string &value) const {
    return make_unique<HostListFilter>(*this, relOp, value);
}
