// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
#include "MonitoringCore.h"
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
    if (const auto *p = columnData<std::unordered_set<Host *>>(row)) {
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
    if (const auto *const p = columnData<hostsmember *>(row)) {
        for (const hostsmember *mem = *p; mem != nullptr; mem = mem->next) {
            host *hst = mem->host_ptr;
            if (auth_user == nullptr ||
                is_authorized_for(_mc->serviceAuthorization(), auth_user, hst,
                                  nullptr)) {
                members.emplace_back(hst->name,
                                     static_cast<HostState>(hst->current_state),
                                     hst->has_been_checked != 0);
            }
        }
    }
#endif
    return members;
}
