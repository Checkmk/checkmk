// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostListRenderer_h
#define HostListRenderer_h

#include "config.h"  // IWYU pragma: keep

#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "ListColumn.h"
#include "auth.h"

#ifdef CMC
#include <unordered_set>
class Host;
#else
#include "nagios.h"
#endif

class ListRenderer;
enum class HostState;

namespace column::host_list {
struct Entry {
    Entry(std::string hn, HostState cs, bool hbc)
        : host_name(std::move(hn)), current_state(cs), has_been_checked(hbc) {}

    std::string host_name;
    HostState current_state;
    bool has_been_checked;
};

template <class T>
class HostListGetter {
#ifdef CMC
    // Relatives may be parents or children (see "childs", sic)
    using relatives_t = std::function<std::unordered_set<Host *>(const T &)>;

public:
    explicit HostListGetter(relatives_t f) : relatives_{std::move(f)} {}

    std::vector<Entry> operator()(const T &t, const User &user) const {
        std::vector<Entry> entries{};
        for (const auto &hst : relatives_(t)) {
            if (user.is_authorized_for_host(*hst)) {
                entries.emplace_back(
                    hst->name(),
                    static_cast<HostState>(hst->state()->current_state_),
                    hst->state()->has_been_checked_);
            }
        }
        return entries;
    }

#else
    using relatives_t = std::function<hostsmember *(const T &)>;

public:
    explicit HostListGetter(relatives_t f) : relatives_{std::move(f)} {}

    std::vector<Entry> operator()(const T &t, const User &user) const {
        std::vector<Entry> entries{};
        for (const hostsmember *mem = relatives_(t); mem != nullptr;
             mem = mem->next) {
            host *hst = mem->host_ptr;
            if (user.is_authorized_for_host(*hst)) {
                entries.emplace_back(hst->name,
                                     static_cast<HostState>(hst->current_state),
                                     hst->has_been_checked != 0);
            }
        }
        return entries;
    }

#endif
private:
    relatives_t relatives_;
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
