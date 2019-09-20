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
#include <algorithm>
#include <iterator>
#include "Renderer.h"
#include "Row.h"

#ifdef CMC
#include <unordered_set>
#include "Host.h"
#include "LogEntry.h"
#include "State.h"
#include "cmc.h"
#else
#include "auth.h"
#include "nagios.h"
#endif

void HostListColumn::output(Row row, RowRenderer &r, const contact *auth_user,
                            std::chrono::seconds /*timezone_offset*/) const {
    ListRenderer l(r);
    for (const auto &member : getMembers(row, auth_user)) {
        if (_show_state) {
            SublistRenderer s(l);
            s.output(member.host_name);
            s.output(static_cast<int>(member.current_state));
            s.output(static_cast<int>(member.has_been_checked));
        } else {
            l.output(member.host_name);
        }
    }
}

std::vector<std::string> HostListColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    auto members = getMembers(row, auth_user);
    std::vector<std::string> host_names;
    std::transform(members.begin(), members.end(),
                   std::back_inserter(host_names),
                   [](const auto &member) { return member.host_name; });
    return host_names;
};

std::vector<HostListColumn::Member> HostListColumn::getMembers(
    Row row, const contact *auth_user) const {
    std::vector<Member> members;
#ifdef CMC
    (void)_mc;  // HACK
    if (auto p = columnData<std::unordered_set<Host *>>(row)) {
        for (const auto &hst : *p) {
            if (auth_user == nullptr || hst->hasContact(auth_user)) {
                members.emplace_back(
                    hst->name(),
                    static_cast<HostState>(hst->state()->_current_state),
                    hst->state()->_has_been_checked);
            }
        }
    }
#else
    if (auto p = columnData<hostsmember *>(row)) {
        for (const hostsmember *mem = *p; mem != nullptr; mem = mem->next) {
            host *hst = mem->host_ptr;
            if (auth_user == nullptr ||
                is_authorized_for(_mc, auth_user, hst, nullptr)) {
                members.emplace_back(hst->name,
                                     static_cast<HostState>(hst->current_state),
                                     hst->has_been_checked != 0);
            }
        }
    }
#endif
    return members;
}
