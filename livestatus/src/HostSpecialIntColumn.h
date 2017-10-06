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

#ifndef HostSpecialIntColumn_h
#define HostSpecialIntColumn_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <string>
#include "IntColumn.h"
#include "contact_fwd.h"
class MonitoringCore;
class Row;

class HostSpecialIntColumn : public IntColumn {
public:
    enum class Type { real_hard_state, pnp_graph_present, mk_inventory_last };

    HostSpecialIntColumn(const std::string& name,
                         const std::string& description, MonitoringCore* mc,
                         Type hsic_type, int indirect_offset, int extra_offset,
                         int extra_extra_offset)
        : IntColumn(name, description, indirect_offset, extra_offset,
                    extra_extra_offset, 0000)
        , _mc(mc)
        , _type(hsic_type) {}
    int32_t getValue(Row row, const contact* auth_user) const override;

private:
    MonitoringCore* _mc;
    const Type _type;
};

#endif  // HostSpecialIntColumn_h
