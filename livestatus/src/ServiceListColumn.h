// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListColumn_h
#define ServiceListColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdint>
#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "ListColumn.h"
#include "Row.h"
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
namespace service_list {
struct Entry {
    Entry(std::string d, ServiceState cs, bool hbc, std::string po,
          ServiceState lhs, uint32_t ca, uint32_t mca, uint32_t sdt, bool a,
          bool spa)
        : description(std::move(d))
        , current_state(cs)
        , has_been_checked(hbc)
        , plugin_output(std::move(po))
        , last_hard_state(lhs)
        , current_attempt(ca)
        , max_check_attempts(mca)
        , scheduled_downtime_depth(sdt)
        , acknowledged(a)
        , service_period_active(spa) {}

    std::string description;
    ServiceState current_state;
    bool has_been_checked;
    std::string plugin_output;
    ServiceState last_hard_state;
    uint32_t current_attempt;
    uint32_t max_check_attempts;
    uint32_t scheduled_downtime_depth;
    bool acknowledged;
    bool service_period_active;
};

}  // namespace service_list
}  // namespace detail

class ServiceListRenderer {
    using function_type =
        std::function<std::vector<detail::service_list::Entry>(
            Row, const contact *)>;

public:
    enum class verbosity { none, low, medium, full };
    ServiceListRenderer(const function_type &f, verbosity v)
        : f_{f}, verbosity_{v} {}
    void operator()(Row row, RowRenderer &r, const contact *auth_user) const;

private:
    function_type f_;
    verbosity verbosity_;
};

class ServiceListColumn : public deprecated::ListColumn {
    using Entry = detail::service_list::Entry;

public:
    ServiceListColumn(const std::string &name, const std::string &description,
                      const ColumnOffsets &offsets, MonitoringCore *mc,
                      ServiceListRenderer::verbosity v)
        : deprecated::ListColumn(name, description, offsets)
        , mc_(mc)
        , renderer_{[this](Row row, const contact *auth_user) {
                        return this->getEntries(row, auth_user);
                    },
                    v} {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds /*timezone_offset*/) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *mc_;
    friend ServiceListRenderer;
    ServiceListRenderer renderer_;
    std::vector<Entry> getEntries(Row row, const contact *auth_user) const;
};

#endif  // ServiceListColumn_h
