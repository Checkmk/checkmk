// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostListColumn.h"

#include <algorithm>
#include <iterator>

#include "Renderer.h"
#include "Row.h"
#include "auth.h"

#ifdef CMC
#include <unordered_set>

#include "Host.h"
#include "LogEntry.h"
#include "State.h"
#else
#include "nagios.h"
#endif

void HostListRenderer::operator()(ListRenderer &l,
                                  const column::hostlist::Entry &entry) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(entry.host_name);
            break;
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(entry.host_name);
            s.output(static_cast<int>(entry.current_state));
            s.output(static_cast<int>(entry.has_been_checked));
            break;
        }
    }
}

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
std::vector<std::string> HostListColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> values;
    auto entries = getEntries(row, auth_user);
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   [](const auto &entry) { return entry.host_name; });
    return values;
};

std::vector<column::hostlist::Entry> HostListColumn::getEntries(
    Row row, const contact *auth_user) const {
    std::vector<column::hostlist::Entry> entries;
#ifdef CMC
    if (const auto *p = columnData<std::unordered_set<Host *>>(row)) {
        for (const auto &hst : *p) {
            if (is_authorized_for_hst(auth_user, hst)) {
                entries.emplace_back(
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
            if (is_authorized_for_hst(auth_user, hst)) {
                entries.emplace_back(hst->name,
                                     static_cast<HostState>(hst->current_state),
                                     hst->has_been_checked != 0);
            }
        }
    }
#endif
    return entries;
}
