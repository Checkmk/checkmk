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

#include "CustomVarsColumn.h"
#include <utility>
#include "Row.h"

#ifdef CMC
#include "Object.h"
#else
#include "nagios.h"
#endif

CustomVarsColumn::CustomVarsColumn(std::string name, std::string description,
                                   int indirect_offset, int extra_offset,
                                   int extra_extra_offset, int offset)
    : Column(std::move(name), std::move(description), indirect_offset,
             extra_offset, extra_extra_offset, offset) {}

CustomVarsColumn::~CustomVarsColumn() = default;

// TODO(sp) This should live in our abstraction layer for cores.
std::unordered_map<std::string, std::string> CustomVarsColumn::getCVM(
    Row row) const {
#ifdef CMC
    auto *object = columnData<Object>(row);
    return object == nullptr ? std::unordered_map<std::string, std::string>()
                             : object->customAttributes();
#else
    std::unordered_map<std::string, std::string> result;
    if (auto p = columnData<customvariablesmember *>(row)) {
        for (auto cvm = *p; cvm != nullptr; cvm = cvm->next) {
            result.emplace(cvm->variable_name, cvm->variable_value);
        }
    }
    return result;
#endif
}

std::string CustomVarsColumn::getVariable(Row row,
                                          const std::string &varname) const {
    auto cvm = getCVM(row);
    auto it = cvm.find(varname);
    return it == cvm.end() ? "" : it->second;
}
