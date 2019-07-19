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

#ifndef LogwatchListColumn_h
#define LogwatchListColumn_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <filesystem>
#include <string>
#include <vector>
#include "ListColumn.h"
#include "contact_fwd.h"
class MonitoringCore;
class Row;

class LogwatchListColumn : public ListColumn {
public:
    LogwatchListColumn(const std::string &name, const std::string &description,
                       int indirect_offset, int extra_offset,
                       int extra_extra_offset, int offset, MonitoringCore *mc)
        : ListColumn(name, description, indirect_offset, extra_offset,
                     extra_extra_offset, offset)
        , _mc(mc) {}

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;

    std::filesystem::path getDirectory(Row row) const;
    std::string getHostName(Row row) const;
};

#endif  // LogwatchListColumn_h
