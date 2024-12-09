// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListRenderer_h
#define HostListRenderer_h

#include <string>
#include <utility>

#include "livestatus/ListColumn.h"

enum class HostState;

namespace column::host_list {
struct Entry {
    Entry(std::string hn, HostState cs, bool hbc)
        : host_name(std::move(hn)), current_state(cs), has_been_checked(hbc) {}

    std::string host_name;
    HostState current_state;
    bool has_been_checked;
};

}  // namespace column::host_list

class HostListRenderer : public ListColumnRenderer<column::host_list::Entry> {
public:
    enum class verbosity { none, full };
    explicit HostListRenderer(verbosity v) : verbosity_{v} {}
    void output(ListRenderer &l,
                const column::host_list::Entry &entry) const override;

private:
    verbosity verbosity_;
};

namespace column::detail {
template <>
inline std::string serialize<::column::host_list::Entry>(
    const ::column::host_list::Entry &e) {
    return e.host_name;
}
}  // namespace column::detail

#endif  // HostListRenderer_h
