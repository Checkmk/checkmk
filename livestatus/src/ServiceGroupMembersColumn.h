// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef ServiceGroupMembersColumn_h
#define ServiceGroupMembersColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include <vector>
#include "Column.h"
#include "ListColumn.h"
#include "opids.h"
class Filter;
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
                              int indirect_offset, int extra_offset,
                              int extra_extra_offset, int offset,
                              MonitoringCore *mc, bool show_state)
        : ListColumn(name, description, indirect_offset, extra_offset,
                     extra_extra_offset, offset)
        , _mc(mc)
        , _show_state(show_state) {}

    void output(Row row, RowRenderer &r,
                const contact *auth_user) const override;

    std::unique_ptr<Filter> createFilter(
        RelationalOperator relOp, const std::string &value) const override;

    std::vector<std::string> getValue(Row row,
                                      const contact *auth_user) const override;

    static std::string separator() { return ""; }

private:
    MonitoringCore *_mc;
    bool _show_state;

    struct Member {
        Member(const std::string &hn, const std::string &d, ServiceState cs,
               bool hbc)
            : host_name(hn)
            , description(d)
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
