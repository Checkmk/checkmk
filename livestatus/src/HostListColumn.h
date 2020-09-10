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
#include "contact_fwd.h"
class ColumnOffsets;
enum class HostState;
class MonitoringCore;
class Row;
class RowRenderer;

class HostListColumn : public ListColumn {
public:
    HostListColumn(const std::string &name, const std::string &description,
                   const ColumnOffsets &offsets, MonitoringCore *mc,
                   bool show_state)
        : ListColumn(name, description, offsets)
        , _mc(mc)
        , _show_state(show_state) {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds /*timezone_offset*/) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;
    const bool _show_state;

    struct Member {
        Member(std::string hn, HostState cs, bool hbc)
            : host_name(std::move(hn))
            , current_state(cs)
            , has_been_checked(hbc) {}

        std::string host_name;
        HostState current_state;
        bool has_been_checked;
    };

    std::vector<Member> getMembers(Row row, const contact *auth_user) const;
};

#endif  // HostListColumn_h
