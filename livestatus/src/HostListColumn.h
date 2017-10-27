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

#ifndef HostListColumn_h
#define HostListColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include <vector>
#include "ListColumn.h"
#include "contact_fwd.h"
enum class HostState;
class MonitoringCore;
class Row;
class RowRenderer;

class HostListColumn : public ListColumn {
public:
    HostListColumn(const std::string &name, const std::string &description,
                   int indirect_offset, int extra_offset,
                   int extra_extra_offset, int offset, MonitoringCore *mc,
                   bool show_state)
        : ListColumn(name, description, indirect_offset, extra_offset,
                     extra_extra_offset, offset)
        , _mc(mc)
        , _show_state(show_state) {}

    void output(Row row, RowRenderer &r,
                const contact *auth_user) const override;

    std::vector<std::string> getValue(Row row,
                                      const contact *auth_user) const override;

private:
    MonitoringCore *_mc;
    const bool _show_state;

    struct Member {
        Member(const std::string &hn, HostState cs, bool hbc)
            : host_name(hn), current_state(cs), has_been_checked(hbc) {}

        std::string host_name;
        HostState current_state;
        bool has_been_checked;
    };

    std::vector<Member> getMembers(Row row, const contact *auth_user) const;
};

#endif  // HostListColumn_h
