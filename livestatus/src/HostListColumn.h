// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListColumn_h
#define HostListColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>
#include <utility>
#include <vector>

#include "ListColumn.h"
#include "Renderer.h"
#include "Row.h"
#include "contact_fwd.h"
class ColumnOffsets;
enum class HostState;

namespace column::hostlist {
struct Entry {
    Entry(std::string hn, HostState cs, bool hbc)
        : host_name(std::move(hn)), current_state(cs), has_been_checked(hbc) {}

    std::string host_name;
    HostState current_state;
    bool has_been_checked;
};
}  // namespace column::hostlist

class HostListRenderer {
public:
    enum class verbosity { none, full };
    explicit HostListRenderer(verbosity v) : verbosity_{v} {}
    void output(ListRenderer &l, const column::hostlist::Entry &entry) const;

private:
    verbosity verbosity_;
};

class HostListColumn : public deprecated::ListColumn {
public:
    HostListColumn(const std::string &name, const std::string &description,
                   const ColumnOffsets &offsets,
                   const HostListRenderer &renderer)
        : deprecated::ListColumn{name, description, offsets}
        , renderer_{renderer} {}

    // Remove once we inherit ListColumn::Callback<T, U>
    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds /*timezone_offset*/) const override {
        ListRenderer l(r);
        for (const auto &entry : this->getRawValue(row, auth_user)) {
            renderer_.output(l, entry);
        }
    }

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    HostListRenderer renderer_;
    std::vector<column::hostlist::Entry> getRawValue(
        Row row, const contact *auth_user) const;
};

#endif  // HostListColumn_h
