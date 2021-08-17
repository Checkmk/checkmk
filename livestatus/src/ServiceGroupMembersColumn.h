// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceGroupMembersColumn_h
#define ServiceGroupMembersColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "Filter.h"
#include "ListColumn.h"
#include "Renderer.h"
#include "Row.h"
#include "opids.h"
class ColumnOffsets;
class MonitoringCore;
enum class ServiceState;

#ifdef CMC
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif

namespace detail {
namespace service_group_members {
struct Entry {
    Entry(std::string hn, std::string d, ServiceState cs, bool hbc)
        : host_name(std::move(hn))
        , description(std::move(d))
        , current_state(cs)
        , has_been_checked(hbc) {}

    std::string host_name;
    std::string description;
    ServiceState current_state;
    bool has_been_checked;
};
}  // namespace service_group_members
}  // namespace detail

class ServiceGroupMembersRenderer {
public:
    enum class verbosity { none, full };
    ServiceGroupMembersRenderer(verbosity v) : verbosity_{v} {}
    void output(ListRenderer &l,
                const detail::service_group_members::Entry &entry) const;

private:
    verbosity verbosity_;
};

class ServiceGroupMembersColumn : public deprecated::ListColumn {
    using Entry = detail::service_group_members::Entry;

public:
    ServiceGroupMembersColumn(const std::string &name,
                              const std::string &description,
                              const ColumnOffsets &offsets,
                              const ServiceGroupMembersRenderer &renderer,
                              MonitoringCore *mc)
        : deprecated::ListColumn(name, description, offsets)
        , renderer_{renderer}
        , mc_{mc} {}

    // CommentColumn::output(), DowntimeColumn::output(),
    // HostListColumn::output(), ServiceGroupMembersColumn::output(),
    // ServiceListColumn::output() are identical.
    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds /*timezone_offset*/) const override {
        ListRenderer l(r);
        for (const auto &entry : this->getEntries(row, auth_user)) {
            renderer_.output(l, entry);
        }
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

    static std::string separator() { return ""; }

private:
    ServiceGroupMembersRenderer renderer_;
    MonitoringCore *mc_;

    std::vector<Entry> getEntries(Row row, const contact *auth_user) const;
};

#endif  // ServiceGroupMembersColumn_h
