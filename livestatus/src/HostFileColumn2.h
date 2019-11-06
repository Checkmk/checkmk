// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

#ifndef HostFileColumn2_h
#define HostFileColumn2_h

#include "config.h"  // IWYU pragma: keep
#include <filesystem>
#include <memory>
#include <string>
#include <vector>
#include "BlobColumn.h"
class Row;

class HostFileColumn2 : public BlobColumn {
public:
    HostFileColumn2(const std::string& name, const std::string& description,
                    int indirect_offset, int extra_offset,
                    int extra_extra_offset, int offset,
                    std::filesystem::path basepath,
                    std::filesystem::path filepath);

    std::unique_ptr<std::vector<char>> getValue(Row row) const override;
    std::filesystem::path basepath() const;
    std::filesystem::path relpath() const;
    std::filesystem::path abspath() const;

private:
    const std::filesystem::path _basepath;
    const std::filesystem::path _relpath;
};

#endif  // HostFileColumn2_h
