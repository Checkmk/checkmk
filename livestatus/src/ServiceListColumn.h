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

#ifndef ServiceListColumn_h
#define ServiceListColumn_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <cstdint>
#include <string>
#include <vector>
#include "ListColumn.h"
class MonitoringCore;
class Row;
class RowRenderer;
enum class ServiceState;

#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

class ServiceListColumn : public ListColumn {
public:
    ServiceListColumn(const std::string &name, const std::string &description,
                      int indirect_offset, int extra_offset,
                      int extra_extra_offset, int offset, MonitoringCore *mc,
                      int info_depth)
        : ListColumn(name, description, indirect_offset, extra_offset,
                     extra_extra_offset, offset)
        , _mc(mc)
        , _info_depth(info_depth) {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;
    int _info_depth;

    struct Entry {
        Entry(const std::string &d, ServiceState cs, bool hbc,
              const std::string &po, ServiceState lhs, uint32_t ca,
              uint32_t mca, uint32_t sdt, bool a, bool spa)
            : description(d)
            , current_state(cs)
            , has_been_checked(hbc)
            , plugin_output(po)
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

    std::vector<Entry> getEntries(Row row, const contact *auth_user) const;
};

#endif  // ServiceListColumn_h
