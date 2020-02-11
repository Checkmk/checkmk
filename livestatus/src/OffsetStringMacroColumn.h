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

#ifndef OffsetStringMacroColumn_h
#define OffsetStringMacroColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <optional>
#include <string>
#include "Column.h"
#include "StringColumn.h"
#include "nagios.h"
class MonitoringCore;
class Row;

class MacroExpander {
public:
    virtual ~MacroExpander() = default;
    virtual std::optional<std::string> expand(const std::string &str) = 0;
    static std::optional<std::string> from_ptr(const char *str);
};

// poor man's monad...
class CompoundMacroExpander : public MacroExpander {
public:
    CompoundMacroExpander(std::unique_ptr<MacroExpander> first,
                          std::unique_ptr<MacroExpander> second);

    std::optional<std::string> expand(const std::string &str) override;

private:
    std::unique_ptr<MacroExpander> _first;
    std::unique_ptr<MacroExpander> _second;
};

class UserMacroExpander : public MacroExpander {
public:
    std::optional<std::string> expand(const std::string &str) override;
};

class CustomVariableExpander : public MacroExpander {
public:
    CustomVariableExpander(std::string prefix, const customvariablesmember *cvm,
                           const MonitoringCore *mc);

    std::optional<std::string> expand(const std::string &str) override;

private:
    std::string _prefix;
    const MonitoringCore *const _mc;
    const customvariablesmember *_cvm;
};

class OffsetStringMacroColumn : public StringColumn {
public:
    // TODO(ml): 5 offsets!
    OffsetStringMacroColumn(const std::string &name,
                            const std::string &description,
                            const Column::Offsets &offsets,
                            const MonitoringCore *mc, int offset)
        : StringColumn(name, description, offsets)
        , _mc(mc)
        , _string_offset(offset) {}

    [[nodiscard]] std::string getValue(Row row) const override;

    [[nodiscard]] virtual std::unique_ptr<MacroExpander> getMacroExpander(
        Row row) const = 0;

protected:
    const MonitoringCore *const _mc;

private:
    const int _string_offset;
};

#endif  // OffsetStringMacroColumn_h
