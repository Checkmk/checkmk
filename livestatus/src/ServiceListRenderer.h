// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ServiceListRenderer_h
#define ServiceListRenderer_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <string>
#include <utility>

#include "ListColumn.h"
enum class ServiceState;
class ListRenderer;

namespace column::service_list {
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

}  // namespace column::service_list

class ServiceListRenderer
    : public ListColumnRenderer<column::service_list::Entry> {
public:
    enum class verbosity { none, low, medium, full };
    explicit ServiceListRenderer(verbosity v) : verbosity_{v} {}
    void output(ListRenderer &l,
                const column::service_list::Entry &entry) const override;

private:
    verbosity verbosity_;
};

namespace column::detail {
template <>
inline std::string serialize<::column::service_list::Entry>(
    const ::column::service_list::Entry &e) {
    return e.description;
}
}  // namespace column::detail

#endif  // ServiceListRenderer_h
