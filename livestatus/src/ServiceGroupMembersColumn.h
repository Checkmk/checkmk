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

#include "Filter.h"
#include "ListColumn.h"
#include "ListFilter.h"  // IWYU pragma: keep
#include "Row.h"
#include "auth.h"
#include "opids.h"
enum class ServiceState;
class Logger;
class ListRenderer;

namespace column::service_group_members {

inline std::string separator() { return ""; }

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

namespace detail {
std::string checkValue(Logger *logger, RelationalOperator relOp,
                       const std::string &value);
}  // namespace detail
}  // namespace column::service_group_members

class ServiceGroupMembersRenderer
    : public ListColumnRenderer<::column::service_group_members::Entry> {
public:
    enum class verbosity { none, full };
    explicit ServiceGroupMembersRenderer(verbosity v) : verbosity_{v} {}
    void output(
        ListRenderer &l,
        const column::service_group_members::Entry &entry) const override;

private:
    verbosity verbosity_;
};

template <class T, class U>
struct ServiceGroupMembersColumn : ListColumn<T, U> {
    using ListColumn<T, U>::ListColumn;
    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;
};

namespace column::detail {
template <>
inline std::string serialize<::column::service_group_members::Entry>(
    const ::column::service_group_members::Entry &entry) {
    return entry.host_name + column::service_group_members::separator() +
           entry.description;
}
}  // namespace column::detail

template <class T, class U>
std::unique_ptr<Filter> ServiceGroupMembersColumn<T, U>::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<ListFilter>(
        kind, this->name(),
        // `timezone_offset` is unused
        [this](Row row, const User &user,
               std::chrono::seconds timezone_offset) {
            return this->getValue(row, user.authUser(), timezone_offset);
        },
        relOp,
        column::service_group_members::detail::checkValue(this->logger(), relOp,
                                                          value),
        this->logger());
}
#endif  // ServiceGroupMembersColumn_h
