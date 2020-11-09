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
#include "opids.h"
class ColumnOffsets;
class MonitoringCore;
class Row;
class RowRenderer;
enum class ServiceState;

#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

class ServiceGroupMembersColumn : public ListColumn {
public:
    ServiceGroupMembersColumn(const std::string &name,
                              const std::string &description,
                              const ColumnOffsets &offsets, MonitoringCore *mc,
                              bool show_state)
        : ListColumn(name, description, offsets)
        , _mc(mc)
        , _show_state(show_state) {}

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
    MonitoringCore *_mc;
    bool _show_state;

    struct Member {
        Member(std::string hn, std::string d, ServiceState cs, bool hbc)
            : host_name(std::move(hn))
            , description(std::move(d))
            , current_state(cs)
            , has_been_checked(hbc) {}

        std::string host_name;
        std::string description;
        ServiceState current_state;
        bool has_been_checked;
    };

    std::vector<Member> getMembers(Row row, const contact *auth_user) const;
};

#endif  // ServiceGroupMembersColumn_h
