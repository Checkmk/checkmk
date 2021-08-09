// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceGroupMembersColumn_h
#define ServiceGroupMembersColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "Filter.h"
#include "ListColumn.h"
#include "Row.h"
#include "opids.h"
class ColumnOffsets;
class MonitoringCore;
class RowRenderer;
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
    using function_type =
        std::function<std::vector<detail::service_group_members::Entry>(
            Row, const contact *)>;

public:
    enum class verbosity { none, full };
    ServiceGroupMembersRenderer(const function_type &f, verbosity v)
        : f_{f}, verbosity_{v} {}
    void operator()(Row row, RowRenderer &r, const contact *auth_user) const;

private:
    function_type f_;
    verbosity verbosity_;
};

class ServiceGroupMembersColumn : public deprecated::ListColumn {
    using Entry = detail::service_group_members::Entry;

public:
    ServiceGroupMembersColumn(const std::string &name,
                              const std::string &description,
                              const ColumnOffsets &offsets, MonitoringCore *mc,
                              ServiceGroupMembersRenderer::verbosity v)
        : deprecated::ListColumn(name, description, offsets)
        , mc_{mc}
        , renderer_{[this](Row row, const contact *auth_user) {
                        return this->getEntries(row, auth_user);
                    },
                    v} {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

    static std::string separator() { return ""; }

private:
    MonitoringCore *mc_;
    friend class ServiceGroupMembersRenderer;
    ServiceGroupMembersRenderer renderer_;

    std::vector<Entry> getEntries(Row row, const contact *auth_user) const;
};

#endif  // ServiceGroupMembersColumn_h
