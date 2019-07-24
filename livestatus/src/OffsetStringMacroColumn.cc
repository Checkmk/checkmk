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

#include "OffsetStringMacroColumn.h"
#include <cstdlib>
#include <type_traits>
#include <utility>
#include "Column.h"
#include "MonitoringCore.h"
#include "RegExp.h"
#include "Row.h"
#include "StringUtils.h"

std::optional<std::string> MacroExpander::from_ptr(const char *str) {
    return str == nullptr ? std::nullopt : std::make_optional(str);
}

CompoundMacroExpander::CompoundMacroExpander(
    std::unique_ptr<MacroExpander> first, std::unique_ptr<MacroExpander> second)
    : _first(std::move(first)), _second(std::move(second)) {}

std::optional<std::string> CompoundMacroExpander::expand(
    const std::string &str) {
    if (auto e = _first->expand(str)) {
        return e;
    }
    return _second->expand(str);
}

std::optional<std::string> UserMacroExpander::expand(const std::string &str) {
    if (mk::starts_with(str, "USER")) {
        int n = atoi(str.substr(4).c_str());
        if (1 <= n && n <= MAX_USER_MACROS) {
            // NOLINTNEXTLINE(cppcoreguidelines-avoid-c-arrays,hicpp-avoid-c-arrays,modernize-avoid-c-arrays)
            extern char *macro_user[MAX_USER_MACROS];
            return from_ptr(macro_user[n - 1]);
        }
    }
    return {};
}

CustomVariableExpander::CustomVariableExpander(std::string prefix,
                                               const customvariablesmember *cvm,
                                               const MonitoringCore *mc)
    : _prefix(std::move(prefix)), _mc(mc), _cvm(cvm) {}

std::optional<std::string> CustomVariableExpander::expand(
    const std::string &str) {
    if (!mk::starts_with(str, _prefix)) {
        return {};
    }

    RegExp re(str.substr(_prefix.size()), RegExp::Case::ignore,
              RegExp::Syntax::literal);
    for (const auto &[name, value] :
         _mc->customAttributes(&_cvm, AttributeKind::custom_variables)) {
        if (re.match(name)) {
            return value;
        }
    }
    return {};
}

namespace {
std::string expandMacros(const std::string &raw,
                         std::unique_ptr<MacroExpander> expander) {
    std::string result;
    size_t pos = 0;
    while (pos < raw.size()) {
        auto start = raw.find('$', pos);
        if (start == std::string::npos) {
            result += raw.substr(pos);
            break;
        }
        auto end = raw.find('$', start + 1);
        if (end == std::string::npos) {
            result += raw.substr(pos);
            break;
        }
        auto macroname = raw.substr(start + 1, end - (start + 1));
        if (auto replacement = expander->expand(macroname)) {
            result += raw.substr(pos, start - pos) + *replacement;
        } else {
            result += raw.substr(pos, end + 1 - pos);
        }
        pos = end + 1;
    }
    return result;
}
}  // namespace

std::string OffsetStringMacroColumn::getValue(Row row) const {
    // TODO(sp): Use _mc!
    (void)_mc;
    if (auto p = columnData<void>(row)) {
        auto s = offset_cast<const char *>(p, _string_offset);
        return *s == nullptr ? "" : expandMacros(*s, getMacroExpander(row));
    }
    return "";
}
